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
from scripts import eval_query_quality
from scripts import runtime_preflight
from services import runtime_service

DEFAULT_OUTPUT_JSON = Path("docs/reports/user_doc_quality_gate_latest.json")
DEFAULT_OUTPUT_REPORT = Path("docs/reports/USER_DOC_QUALITY_GATE_LATEST.md")
DEFAULT_EVAL_FILE = Path("evals/user_doc_answer_level_eval_fixtures.jsonl")
DEFAULT_GATE_BUCKETS = {"user-doc-candidate"}
DEFAULT_GATE_CASE_IDS = {"UDQ-BC-01"}
DEFAULT_REQUIRED_COLLECTION_KEYS = ["project_docs"]
DEFAULT_QUERY_TIMEOUT_SECONDS = 60

PROJECT_DOCS_REINDEX_HINT = (
    "Run project_docs reindex before this opt-in gate: "
    "./.venv/bin/python -c \"from services import index_service; import json; "
    "result=index_service.reindex_single_collection(reset=False, collection_key='project_docs'); "
    "print(json.dumps(result, ensure_ascii=False, indent=2))\""
)


def selected_items(items: set[str] | None, default: set[str]) -> set[str]:
    return {item.strip() for item in (items or default) if item.strip()}


def summarize_collection_vectors(
    collections_payload: dict[str, object],
    *,
    required_keys: list[str] | None = None,
) -> dict[str, object]:
    required = required_keys or list(DEFAULT_REQUIRED_COLLECTION_KEYS)
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
        "support_pass_rate": 0.0,
        "source_route_pass_rate": 0.0,
        "bucket_summaries": {},
    }


def gate_boundary() -> dict[str, object]:
    return {
        "default_release_gate": "generic-baseline",
        "default_release_gate_command": "scripts/check_ops_baseline_gate.py",
        "user_doc_gate": "user-doc-candidate",
        "user_doc_eval_file": str(DEFAULT_EVAL_FILE),
        "required_collection_keys": list(DEFAULT_REQUIRED_COLLECTION_KEYS),
        "default_runtime_collection_changed": False,
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
    support_pass_rate = float(eval_summary.get("support_pass_rate", 0.0) or 0.0)
    source_route_pass_rate = float(eval_summary.get("source_route_pass_rate", 0.0) or 0.0)
    return (
        cases > 0
        and passed == cases
        and pass_rate == 1.0
        and support_pass_rate == 1.0
        and source_route_pass_rate == 1.0
    )


def find_runtime_check(runtime_report: dict[str, object], name: str) -> dict[str, object] | None:
    for check in runtime_report.get("checks", []):
        if isinstance(check, dict) and str(check.get("name", "")).strip() == name:
            return check
    return None


def required_collection_keys_from_fixtures(fixtures: list[dict[str, object]]) -> list[str]:
    keys = sorted(
        {
            str(key).strip()
            for fixture in fixtures
            for key in fixture.get("collection_keys", [])
            if str(key).strip()
        }
    )
    return keys or list(DEFAULT_REQUIRED_COLLECTION_KEYS)


def build_blocked_report(
    *,
    base_url: str,
    llm_provider: str,
    llm_model: str | None,
    eval_file: Path,
    selected_buckets: set[str],
    selected_case_ids: set[str],
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
            "selected_buckets": sorted(selected_buckets),
            "selected_case_ids": sorted(selected_case_ids),
            "summary": empty_eval_summary(),
            "health": eval_health or {},
            "results": [],
        },
        "boundary": gate_boundary(),
    }


def build_gate_report(
    *,
    base_url: str,
    timeout_seconds: int,
    eval_file: Path,
    buckets: set[str] | None,
    case_ids: set[str] | None,
    llm_provider: str,
    llm_model: str | None,
    llm_base_url: str | None,
    llm_api_key: str | None,
    query_timeout_seconds: int,
) -> dict[str, object]:
    selected_buckets = selected_items(buckets, DEFAULT_GATE_BUCKETS)
    selected_case_ids = selected_items(case_ids, DEFAULT_GATE_CASE_IDS)
    runtime_report = runtime_preflight.build_report(
        app_base_url=base_url,
        timeout_seconds=timeout_seconds,
        llm_provider=llm_provider,
        llm_model=llm_model,
        llm_base_url=llm_base_url,
        embedding_model=runtime_service.get_embedding_model(),
    )

    try:
        fixtures = eval_query_quality.load_eval_fixtures(
            (ROOT_DIR / eval_file).resolve() if not eval_file.is_absolute() else eval_file,
            buckets=selected_buckets,
            case_ids=selected_case_ids,
        )
    except Exception as exc:
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            selected_buckets=selected_buckets,
            selected_case_ids=selected_case_ids,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "USER_DOC_FIXTURE_LOAD_FAILED",
                    "message": str(exc),
                    "hint": "Check evals/user_doc_answer_level_eval_fixtures.jsonl and selected case IDs.",
                }
            ],
        )

    required_keys = required_collection_keys_from_fixtures(fixtures)
    app_health = find_runtime_check(runtime_report, "app_health") or {}
    if not bool(app_health.get("ready")):
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            selected_buckets=selected_buckets,
            selected_case_ids=selected_case_ids,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "APP_HEALTH_UNREACHABLE",
                    "message": str(app_health.get("message", "health endpoint unreachable")),
                    "hint": "Start the local app server before running the user-doc quality gate.",
                }
            ],
            collection_summary=summarize_collection_vectors(
                {"collections": []},
                required_keys=required_keys,
            ),
        )

    try:
        collections_payload = eval_query_quality.collections_check(base_url, timeout_seconds)
    except Exception as exc:
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            selected_buckets=selected_buckets,
            selected_case_ids=selected_case_ids,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "COLLECTIONS_CHECK_FAILED",
                    "message": str(exc),
                    "hint": "Check /collections and confirm the expected Trunk RAG app is using this port.",
                }
            ],
            collection_summary=summarize_collection_vectors(
                {"collections": []},
                required_keys=required_keys,
            ),
            eval_health=dict(app_health.get("payload", {})) if isinstance(app_health.get("payload"), dict) else {},
        )

    collection_summary = summarize_collection_vectors(collections_payload, required_keys=required_keys)
    if not bool(collection_summary.get("ready")):
        missing = ", ".join(collection_summary.get("missing_keys", []))
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            selected_buckets=selected_buckets,
            selected_case_ids=selected_case_ids,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "PROJECT_DOCS_REINDEX_REQUIRED",
                    "message": f"Required user-doc collections have no vectors: {missing}",
                    "hint": PROJECT_DOCS_REINDEX_HINT,
                }
            ],
            collection_summary=collection_summary,
            eval_health=dict(app_health.get("payload", {})) if isinstance(app_health.get("payload"), dict) else {},
        )

    try:
        eval_payload = eval_query_quality.run_evaluation(
            backend="vector_query",
            base_url=base_url,
            timeout_seconds=timeout_seconds,
            eval_file=eval_file,
            buckets=selected_buckets,
            case_ids=selected_case_ids,
            llm_provider=llm_provider,
            llm_model=llm_model,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            query_timeout_seconds=query_timeout_seconds,
            debug=True,
        )
    except Exception as exc:
        return build_blocked_report(
            base_url=base_url,
            llm_provider=llm_provider,
            llm_model=llm_model,
            eval_file=eval_file,
            selected_buckets=selected_buckets,
            selected_case_ids=selected_case_ids,
            runtime_report=runtime_report,
            diagnostics=[
                {
                    "code": "USER_DOC_EVAL_FAILED",
                    "message": str(exc),
                    "hint": "Re-run project_docs reindex if docs changed; otherwise inspect the eval error.",
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
    diagnostics: list[dict[str, str]] = []
    if not ready:
        diagnostics.append(
            {
                "code": "USER_DOC_EVAL_NOT_READY",
                "message": "Selected user-doc eval cases did not fully pass.",
                "hint": "Inspect eval results. If source coverage is stale, reindex project_docs and retry.",
            }
        )
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "ready": ready,
        "base_url": base_url,
        "llm_provider": llm_provider,
        "llm_model": llm_model,
        "runtime": runtime_report,
        "diagnostics": diagnostics,
        "collections": collection_summary,
        "eval": {
            "eval_file": str(eval_file),
            "selected_buckets": sorted(selected_buckets),
            "selected_case_ids": sorted(selected_case_ids),
            "summary": eval_payload["summary"],
            "health": eval_payload["health"],
            "results": eval_payload["results"],
        },
        "boundary": gate_boundary(),
    }


def build_markdown_report(report: dict[str, object]) -> str:
    eval_summary = dict(report["eval"]["summary"])
    runtime_report = dict(report.get("runtime", {}))
    boundary = dict(report["boundary"])
    lines = [
        "# User-Doc Quality Gate Report",
        "",
        f"- generated_at: `{report['generated_at']}`",
        f"- ready: `{report['ready']}`",
        f"- base_url: `{report['base_url']}`",
        f"- llm_provider: `{report['llm_provider']}`",
        f"- llm_model: `{report['llm_model'] or '-'}`",
        "",
        "## Gate Boundary",
        f"- default_release_gate: `{boundary['default_release_gate']}`",
        f"- default_release_gate_command: `{boundary['default_release_gate_command']}`",
        f"- user_doc_gate: `{boundary['user_doc_gate']}`",
        f"- user_doc_eval_file: `{boundary['user_doc_eval_file']}`",
        f"- required_collection_keys: `{', '.join(boundary['required_collection_keys'])}`",
        f"- default_runtime_collection_changed: `{boundary['default_runtime_collection_changed']}`",
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
    lines.extend(["", "## User-Doc Collections"])
    for item in report["collections"]["items"]:
        lines.append(f"- {item['key']}: vectors=`{item['vectors']}`, ready=`{item['ready']}`")
    if report.get("diagnostics"):
        lines.extend(["", "## Diagnostics"])
        for diagnostic in report["diagnostics"]:
            if not isinstance(diagnostic, dict):
                continue
            lines.append(
                f"- {diagnostic.get('code', '-')}: `{diagnostic.get('message', '-')}` / "
                f"hint=`{diagnostic.get('hint', '-')}`"
            )
    lines.extend(
        [
            "",
            "## Eval Target",
            f"- selected_buckets: `{', '.join(report['eval'].get('selected_buckets', [])) or '-'}`",
            f"- selected_case_ids: `{', '.join(report['eval'].get('selected_case_ids', [])) or '-'}`",
            "",
            "## User-Doc Eval",
            f"- cases: `{eval_summary['cases']}`",
            f"- passed: `{eval_summary['passed']}`",
            f"- pass_rate: `{eval_summary['pass_rate']}`",
            f"- avg_weighted_score: `{eval_summary['avg_weighted_score']}`",
            f"- support_pass_rate: `{eval_summary.get('support_pass_rate', 0.0)}`",
            f"- source_route_pass_rate: `{eval_summary.get('source_route_pass_rate', 0.0)}`",
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
        description="Check the opt-in project_docs user-doc answer quality gate."
    )
    parser.add_argument("--base-url", type=str, default="http://127.0.0.1:8000")
    parser.add_argument("--timeout-seconds", type=int, default=90)
    parser.add_argument("--eval-file", type=Path, default=DEFAULT_EVAL_FILE)
    parser.add_argument("--bucket", action="append", default=[])
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--llm-provider", type=str)
    parser.add_argument("--llm-model", type=str)
    parser.add_argument("--llm-base-url", type=str)
    parser.add_argument("--llm-api-key", type=str)
    parser.add_argument("--query-timeout-seconds", type=int, default=DEFAULT_QUERY_TIMEOUT_SECONDS)
    parser.add_argument("--output-json", type=Path)
    parser.add_argument("--output-report", type=Path)
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def print_human_readable(report: dict[str, object]) -> None:
    overall = "ready" if report["ready"] else "blocked"
    print(f"[user-doc-quality-gate] {overall}")
    print(f"  base_url={report['base_url']}")
    print(f"  llm={report['llm_provider']}:{report['llm_model']}")
    print("  boundary:")
    print(f"    - default_release_gate={report['boundary']['default_release_gate']}")
    print(f"    - user_doc_gate={report['boundary']['user_doc_gate']}")
    print(f"    - default_runtime_collection_changed={report['boundary']['default_runtime_collection_changed']}")
    runtime_report = dict(report.get("runtime", {}))
    print(f"  runtime_ready={runtime_report.get('ready', False)}")
    for check in runtime_report.get("checks", []):
        if not isinstance(check, dict):
            continue
        status = "ready" if check.get("ready") else "blocked"
        print(f"    - {check.get('name')}: {status} ({check.get('message')})")
    print("  user_doc_collections:")
    for item in report["collections"]["items"]:
        status = "ready" if item["ready"] else "blocked"
        print(f"    - {item['key']}: {status} ({item['vectors']} vectors)")
    if report.get("diagnostics"):
        print("  diagnostics:")
        for diagnostic in report["diagnostics"]:
            if not isinstance(diagnostic, dict):
                continue
            print(
                f"    - {diagnostic.get('code')}: {diagnostic.get('message')} | "
                f"hint={diagnostic.get('hint')}"
            )
    eval_summary = report["eval"]["summary"]
    print(f"  eval_buckets={','.join(report['eval'].get('selected_buckets', [])) or '-'}")
    print(f"  eval_case_ids={','.join(report['eval'].get('selected_case_ids', [])) or '-'}")
    print(
        "  eval:"
        f" cases={eval_summary['cases']}"
        f" passed={eval_summary['passed']}"
        f" pass_rate={eval_summary['pass_rate']}"
        f" support_pass_rate={eval_summary.get('support_pass_rate', 0.0)}"
        f" source_route_pass_rate={eval_summary.get('source_route_pass_rate', 0.0)}"
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
        buckets={item.strip() for item in args.bucket if item.strip()} or DEFAULT_GATE_BUCKETS,
        case_ids={item.strip() for item in args.case_id if item.strip()} or DEFAULT_GATE_CASE_IDS,
        llm_provider=(args.llm_provider or str(default_llm["provider"] or "ollama")).strip(),
        llm_model=(args.llm_model or str(default_llm["model"] or "")).strip() or None,
        llm_base_url=(args.llm_base_url or str(default_llm["base_url"] or "")).strip() or None,
        llm_api_key=(args.llm_api_key or "").strip() or None,
        query_timeout_seconds=args.query_timeout_seconds,
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
