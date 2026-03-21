from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common import load_project_env
from core.settings import COLLECTION_CONFIGS
from scripts import eval_query_quality
from scripts import runtime_preflight
from services import runtime_service

DEFAULT_OUTPUT_JSON = Path("docs/reports/ops_baseline_gate_latest.json")
DEFAULT_OUTPUT_REPORT = Path("docs/reports/OPS_BASELINE_GATE_LATEST.md")


def summarize_collection_vectors(
    collections_payload: dict[str, object],
    *,
    required_keys: list[str] | None = None,
) -> dict[str, object]:
    required = required_keys or list(COLLECTION_CONFIGS.keys())
    vector_counts = {
        str(item.get("key", "")).strip(): int(item.get("vectors", 0) or 0)
        for item in collections_payload.get("collections", [])
        if isinstance(item, dict)
    }
    items: list[dict[str, object]] = []
    missing: list[str] = []
    for key in required:
        vectors = vector_counts.get(key, 0)
        ready = vectors > 0
        if not ready:
            missing.append(key)
        items.append({"key": key, "vectors": vectors, "ready": ready})
    return {
        "required_keys": required,
        "items": items,
        "missing_keys": missing,
        "ready": not missing,
    }


def empty_eval_summary() -> dict[str, object]:
    return {
        "cases": 0,
        "passed": 0,
        "pass_rate": 0.0,
        "avg_latency_ms": 0.0,
        "p95_latency_ms": 0.0,
        "avg_weighted_score": 0.0,
        "bucket_summaries": {},
    }


def evaluate_gate_ready(
    *,
    runtime_ready: bool,
    collection_summary: dict[str, object],
    eval_summary: dict[str, object],
) -> bool:
    if not runtime_ready:
        return False
    if not bool(collection_summary.get("ready")):
        return False
    cases = int(eval_summary.get("cases", 0) or 0)
    passed = int(eval_summary.get("passed", 0) or 0)
    pass_rate = float(eval_summary.get("pass_rate", 0.0) or 0.0)
    return cases > 0 and passed == cases and pass_rate == 1.0


def find_runtime_check(runtime_report: dict[str, object], name: str) -> dict[str, object] | None:
    for check in runtime_report.get("checks", []):
        if isinstance(check, dict) and str(check.get("name", "")).strip() == name:
            return check
    return None


def build_blocked_report(
    *,
    base_url: str,
    llm_provider: str,
    llm_model: str | None,
    eval_file: Path,
    runtime_report: dict[str, object],
    diagnostics: list[dict[str, str]],
    collection_summary: dict[str, object] | None = None,
    eval_health: dict[str, object] | None = None,
) -> dict[str, object]:
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "ready": False,
        "base_url": base_url,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "runtime": runtime_report,
        "diagnostics": diagnostics,
        "collections": collection_summary or summarize_collection_vectors({"collections": []}),
        "eval": {
            "eval_file": str(eval_file),
            "summary": empty_eval_summary(),
            "health": eval_health or {},
            "results": [],
        },
    }


def build_gate_report(
    *,
    base_url: str,
    timeout_seconds: int,
    eval_file: Path,
    llm_provider: str,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
) -> dict[str, object]:
    runtime_report = runtime_preflight.build_report(
        app_base_url=base_url,
        timeout_seconds=timeout_seconds,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        embedding_model=runtime_service.get_embedding_model(),
    )
    app_health = find_runtime_check(runtime_report, "app_health") or {}
    if not bool(app_health.get("ready")):
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "APP_HEALTH_UNREACHABLE",
                    "message": str(app_health.get("message", "health endpoint unreachable")),
                    "hint": "먼저 run_doc_rag.bat 또는 ./.venv/bin/python app_api.py 로 서버를 실행하세요.",
                }
            ],
        )

    try:
        collections_payload = eval_query_quality.collections_check(base_url, timeout_seconds)
    except Exception as exc:
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "COLLECTIONS_CHECK_FAILED",
                    "message": str(exc),
                    "hint": "/collections 응답이 정상인지, 그리고 같은 포트에 다른 앱이 떠 있지 않은지 확인하세요.",
                }
            ],
            eval_health=dict(app_health.get("payload", {})) if isinstance(app_health.get("payload"), dict) else {},
        )

    collection_summary = summarize_collection_vectors(collections_payload)
    try:
        eval_payload = eval_query_quality.run_evaluation(
            backend="vector_query",
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            eval_file=eval_file,
            buckets={"ops-baseline"},
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
        )
    except Exception as exc:
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "OPS_EVAL_FAILED",
                    "message": str(exc),
                    "hint": "Reindex 이후 다시 실행하고, LLM 런타임과 기본 모델 준비 상태를 확인하세요.",
                }
            ],
            collection_summary=collection_summary,
            eval_health=dict(app_health.get("payload", {})) if isinstance(app_health.get("payload"), dict) else {},
        )

    ready = evaluate_gate_ready(
        runtime_ready=bool(runtime_report.get("ready")),
        collection_summary=collection_summary,
        eval_summary=dict(eval_payload["summary"]),
    )
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "ready": ready,
        "base_url": base_url,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "runtime": runtime_report,
        "diagnostics": [],
        "collections": collection_summary,
        "eval": {
            "eval_file": str(eval_file),
            "summary": eval_payload["summary"],
            "health": eval_payload["health"],
            "results": eval_payload["results"],
        },
    }


def build_markdown_report(report: dict[str, object]) -> str:
    collection_summary = dict(report["collections"])
    eval_summary = dict(report["eval"]["summary"])
    runtime_report = dict(report.get("runtime", {}))
    lines = [
        "# Ops Baseline Gate Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- ready: `{report['ready']}`",
        f"- base_url: `{report['base_url']}`",
        f"- llm_provider: `{report['llm_provider']}`",
        f"- llm_model: `{report['llm_model'] or '-'}`",
        "",
        "## Runtime Preflight",
        f"- ready: `{runtime_report.get('ready', False)}`",
    ]
    for check in runtime_report.get("checks", []):
        if not isinstance(check, dict):
            continue
        lines.append(
            f"- {check.get('name', '-')}: ready=`{check.get('ready', False)}` message=`{check.get('message', '-')}`"
        )
    lines.extend(
        [
            "",
            "## All-Routes Collections",
        ]
    )
    for item in collection_summary["items"]:
        lines.append(f"- {item['key']}: vectors=`{item['vectors']}`, ready=`{item['ready']}`")
    if report.get("diagnostics"):
        lines.extend(["", "## Diagnostics"])
        for diagnostic in report["diagnostics"]:
            if not isinstance(diagnostic, dict):
                continue
            lines.append(
                f"- {diagnostic.get('code', '-')}: `{diagnostic.get('message', '-')}` / hint=`{diagnostic.get('hint', '-')}`"
            )
    lines.extend(
        [
            "",
            "## Ops Baseline Eval",
            f"- cases: `{eval_summary['cases']}`",
            f"- passed: `{eval_summary['passed']}`",
            f"- pass_rate: `{eval_summary['pass_rate']}`",
            f"- avg_weighted_score: `{eval_summary['avg_weighted_score']}`",
            f"- avg_latency_ms: `{eval_summary['avg_latency_ms']}`",
            f"- p95_latency_ms: `{eval_summary['p95_latency_ms']}`",
        ]
    )
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, object], *, output_json: Path, output_report: Path) -> None:
    resolved_json = (ROOT_DIR / output_json).resolve() if not output_json.is_absolute() else output_json
    resolved_report = (ROOT_DIR / output_report).resolve() if not output_report.is_absolute() else output_report
    resolved_json.parent.mkdir(parents=True, exist_ok=True)
    resolved_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    resolved_report.parent.mkdir(parents=True, exist_ok=True)
    resolved_report.write_text(build_markdown_report(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check the ops-baseline regression gate and all-routes vector readiness."
    )
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=int, default=45)
    parser.add_argument("--eval-file", type=Path, default=Path("evals/answer_level_eval_fixtures.jsonl"))
    parser.add_argument("--llm-provider", type=str)
    parser.add_argument("--llm-model", type=str)
    parser.add_argument("--llm-base-url", type=str)
    parser.add_argument("--llm-api-key", type=str)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def print_human_readable(report: dict[str, object]) -> None:
    overall = "ready" if report["ready"] else "blocked"
    print(f"[ops-baseline-gate] {overall}")
    print(f"  base_url={report['base_url']}")
    print(f"  llm={report['llm_provider']}:{report['llm_model']}")
    runtime_report = dict(report.get("runtime", {}))
    print(f"  runtime_ready={runtime_report.get('ready', False)}")
    for check in runtime_report.get("checks", []):
        if not isinstance(check, dict):
            continue
        status = "ready" if check.get("ready") else "blocked"
        print(f"    - {check.get('name')}: {status} ({check.get('message')})")
    print("  all_routes:")
    for item in report["collections"]["items"]:
        status = "ready" if item["ready"] else "blocked"
        print(f"    - {item['key']}: {status} ({item['vectors']} vectors)")
    if report.get("diagnostics"):
        print("  diagnostics:")
        for diagnostic in report["diagnostics"]:
            if not isinstance(diagnostic, dict):
                continue
            print(
                f"    - {diagnostic.get('code')}: {diagnostic.get('message')} | hint={diagnostic.get('hint')}"
            )
    eval_summary = report["eval"]["summary"]
    print(
        "  eval:"
        f" cases={eval_summary['cases']}"
        f" passed={eval_summary['passed']}"
        f" pass_rate={eval_summary['pass_rate']}"
        f" avg_weighted_score={eval_summary['avg_weighted_score']}"
        f" p95_latency_ms={eval_summary['p95_latency_ms']}"
    )


def main() -> int:
    args = parse_args()
    env_path = load_project_env()
    if env_path:
        print(f"Loaded env: {env_path}", file=sys.stderr)

    default_llm = runtime_service.get_default_llm_config()
    report = build_gate_report(
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        eval_file=args.eval_file,
        llm_provider=(args.llm_provider or str(default_llm["provider"] or "ollama")).strip(),
        llm_model=(args.llm_model or str(default_llm["model"] or "")).strip() or None,
        llm_base_url=(args.llm_base_url or str(default_llm["base_url"] or "")).strip() or None,
        llm_api_key=(args.llm_api_key or "").strip() or None,
    )

    if args.output_json or args.output_report:
        write_outputs(
            report,
            output_json=args.output_json or DEFAULT_OUTPUT_JSON,
            output_report=args.output_report or DEFAULT_OUTPUT_REPORT,
        )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print_human_readable(report)

    return 0 if report["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
