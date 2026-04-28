from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from scripts import eval_query_quality

DEFAULT_OUTPUT_JSON = Path("docs/reports/rag_quality_model_comparison_latest.json")
DEFAULT_OUTPUT_REPORT = Path("docs/reports/RAG_QUALITY_MODEL_COMPARISON_LATEST.md")
DEFAULT_BUCKETS = ["generic-baseline", "sample-pack-baseline"]
DEFAULT_MIN_PASS_RATE = 1.0
DEFAULT_MIN_AVG_WEIGHTED_SCORE = 0.85
DEFAULT_MAX_P95_MS = 20_000.0
SUPPORTED_PROVIDERS = {"ollama", "groq", "lmstudio", "openai"}


@dataclass(frozen=True)
class ModelSpec:
    provider: str
    model: str

    @property
    def label(self) -> str:
        return f"{self.provider}:{self.model}"


def parse_model_spec(value: str, *, default_provider: str) -> ModelSpec:
    raw = value.strip()
    if not raw:
        raise ValueError("--model accepts non-empty values only")
    provider_candidate, separator, model_candidate = raw.partition(":")
    if separator and provider_candidate in SUPPORTED_PROVIDERS:
        model = model_candidate.strip()
        if not model:
            raise ValueError(f"model name is empty in {value!r}")
        return ModelSpec(provider=provider_candidate, model=model)
    return ModelSpec(provider=default_provider, model=raw)


def _metric_check(name: str, passed: bool, actual: object, expected: str) -> dict[str, object]:
    return {
        "name": name,
        "pass": passed,
        "actual": actual,
        "expected": expected,
    }


def evaluate_gate(
    summary: dict[str, object],
    *,
    required_buckets: list[str],
    min_pass_rate: float,
    min_avg_weighted_score: float,
    max_p95_ms: float,
) -> dict[str, object]:
    checks: list[dict[str, object]] = []
    pass_rate = float(summary.get("pass_rate", 0.0) or 0.0)
    avg_score = float(summary.get("avg_weighted_score", 0.0) or 0.0)
    p95_ms = float(summary.get("p95_latency_ms", 0.0) or 0.0)
    support_pass_rate = float(summary.get("support_pass_rate", 0.0) or 0.0)

    checks.append(
        _metric_check(
            "overall_pass_rate",
            pass_rate >= min_pass_rate,
            pass_rate,
            f">= {min_pass_rate}",
        )
    )
    checks.append(
        _metric_check(
            "overall_avg_weighted_score",
            avg_score >= min_avg_weighted_score,
            avg_score,
            f">= {min_avg_weighted_score}",
        )
    )
    checks.append(
        _metric_check(
            "overall_p95_latency_ms",
            p95_ms <= max_p95_ms,
            p95_ms,
            f"<= {max_p95_ms}",
        )
    )
    checks.append(
        _metric_check(
            "overall_support_pass_rate",
            support_pass_rate >= min_pass_rate,
            support_pass_rate,
            f">= {min_pass_rate}",
        )
    )

    bucket_summaries = summary.get("bucket_summaries", {})
    if not isinstance(bucket_summaries, dict):
        bucket_summaries = {}
    for bucket in required_buckets:
        bucket_summary = bucket_summaries.get(bucket)
        if not isinstance(bucket_summary, dict):
            checks.append(_metric_check(f"{bucket}.exists", False, "-", "present"))
            continue
        bucket_pass_rate = float(bucket_summary.get("pass_rate", 0.0) or 0.0)
        bucket_score = float(bucket_summary.get("avg_weighted_score", 0.0) or 0.0)
        bucket_p95 = float(bucket_summary.get("p95_latency_ms", 0.0) or 0.0)
        bucket_support_pass_rate = float(bucket_summary.get("support_pass_rate", 0.0) or 0.0)
        checks.extend(
            [
                _metric_check(
                    f"{bucket}.pass_rate",
                    bucket_pass_rate >= min_pass_rate,
                    bucket_pass_rate,
                    f">= {min_pass_rate}",
                ),
                _metric_check(
                    f"{bucket}.avg_weighted_score",
                    bucket_score >= min_avg_weighted_score,
                    bucket_score,
                    f">= {min_avg_weighted_score}",
                ),
                _metric_check(
                    f"{bucket}.p95_latency_ms",
                    bucket_p95 <= max_p95_ms,
                    bucket_p95,
                    f"<= {max_p95_ms}",
                ),
                _metric_check(
                    f"{bucket}.support_pass_rate",
                    bucket_support_pass_rate >= min_pass_rate,
                    bucket_support_pass_rate,
                    f">= {min_pass_rate}",
                ),
            ]
        )

    return {
        "ready": all(bool(check["pass"]) for check in checks),
        "checks": checks,
    }


def summarize_failed_cases(results: list[dict[str, object]]) -> list[dict[str, object]]:
    failed: list[dict[str, object]] = []
    for result in results:
        if result.get("pass") and result.get("support_pass"):
            continue
        failed.append(
            {
                "id": result.get("id"),
                "bucket": result.get("bucket"),
                "pass": result.get("pass"),
                "weighted_score": result.get("weighted_score"),
                "latency_ms": result.get("latency_ms"),
                "required_hits": f"{len(result.get('required_hits', []))}/{result.get('required_total', 0)}",
                "must_include_any_hits": (
                    f"{len(result.get('must_include_any_hits', []))}/"
                    f"{result.get('must_include_any_total', 0)}"
                ),
                "support_level": result.get("support_level"),
                "citation_count": result.get("citation_count"),
                "source_route_coverage_ratio": result.get("source_route_coverage_ratio"),
                "answer_preview": result.get("answer_preview"),
                "error_code": result.get("error_code"),
            }
        )
    return failed


def build_report(
    *,
    model_payloads: list[dict[str, object]],
    required_buckets: list[str],
    min_pass_rate: float,
    min_avg_weighted_score: float,
    max_p95_ms: float,
    selected_buckets: list[str],
    eval_file: Path,
    base_url: str,
    timeout_seconds: int,
    query_timeout_seconds: int | None,
    quality_mode: str | None,
    quality_stage: str | None,
) -> dict[str, object]:
    models: list[dict[str, object]] = []
    for payload in model_payloads:
        summary = dict(payload["summary"])
        gate = evaluate_gate(
            summary,
            required_buckets=required_buckets,
            min_pass_rate=min_pass_rate,
            min_avg_weighted_score=min_avg_weighted_score,
            max_p95_ms=max_p95_ms,
        )
        models.append(
            {
                "provider": payload["llm_provider"],
                "model": payload["llm_model"],
                "label": f"{payload['llm_provider']}:{payload['llm_model']}",
                "gate": gate,
                "summary": summary,
                "failed_cases": summarize_failed_cases(list(payload["results"])),
                "raw_payload": payload,
            }
        )

    ready_models = [item for item in models if item["gate"]["ready"]]
    ranked_models = sorted(
        models,
        key=lambda item: (
            bool(item["gate"]["ready"]),
            float(item["summary"].get("pass_rate", 0.0) or 0.0),
            float(item["summary"].get("avg_weighted_score", 0.0) or 0.0),
            -float(item["summary"].get("p95_latency_ms", 0.0) or 0.0),
        ),
        reverse=True,
    )
    selected = ranked_models[0] if ranked_models else None
    outcome = "ready" if ready_models else "blocked"
    if selected and selected["gate"]["ready"]:
        recommendation = f"`{selected['label']}` satisfies the selected RAG quality gate."
    elif selected:
        recommendation = (
            f"`{selected['label']}` is the strongest measured candidate, but no model satisfies "
            "the selected RAG quality gate."
        )
    else:
        recommendation = "No model payload was evaluated."

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "outcome": outcome,
        "recommendation": recommendation,
        "selected_candidate": None if selected is None else selected["label"],
        "selected_buckets": selected_buckets,
        "required_buckets": required_buckets,
        "thresholds": {
            "min_pass_rate": min_pass_rate,
            "min_avg_weighted_score": min_avg_weighted_score,
            "max_p95_ms": max_p95_ms,
        },
        "eval_file": str(eval_file),
        "base_url": base_url,
        "timeout_seconds": timeout_seconds,
        "query_timeout_seconds": query_timeout_seconds,
        "quality_mode": quality_mode,
        "quality_stage": quality_stage,
        "models": models,
    }


def build_markdown_report(report: dict[str, object]) -> str:
    thresholds = dict(report["thresholds"])
    lines = [
        "# RAG Quality Model Comparison",
        "",
        "## Scope",
        f"- generated_at: `{report['generated_at']}`",
        f"- outcome: `{report['outcome']}`",
        f"- recommendation: {report['recommendation']}",
        f"- selected_candidate: `{report.get('selected_candidate') or '-'}`",
        f"- eval_file: `{report['eval_file']}`",
        f"- base_url: `{report['base_url']}`",
        f"- http_timeout_seconds: `{report['timeout_seconds']}`",
        f"- query_timeout_seconds: `{report.get('query_timeout_seconds') or '-'}`",
        f"- quality_mode: `{report.get('quality_mode') or '-'}`",
        f"- quality_stage: `{report.get('quality_stage') or '-'}`",
        f"- selected_buckets: `{', '.join(report['selected_buckets'])}`",
        f"- required_buckets: `{', '.join(report['required_buckets'])}`",
        f"- min_pass_rate: `{thresholds['min_pass_rate']}`",
        f"- min_avg_weighted_score: `{thresholds['min_avg_weighted_score']}`",
        f"- max_p95_ms: `{thresholds['max_p95_ms']}`",
        "",
        "## Model Summary",
        "",
        "| model | gate | cases | passed | pass_rate | score | support | p95_ms | failed_cases |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for model in report["models"]:
        summary = model["summary"]
        gate = "ready" if model["gate"]["ready"] else "blocked"
        lines.append(
            f"| `{model['label']}` | {gate} | {summary['cases']} | {summary['passed']} | "
            f"{summary['pass_rate']} | {summary['avg_weighted_score']} | "
            f"{summary.get('support_pass_rate', 0.0)} | {summary['p95_latency_ms']} | "
            f"{len(model['failed_cases'])} |"
        )

    lines.extend(["", "## Bucket Summary"])
    for model in report["models"]:
        lines.extend(["", f"### {model['label']}"])
        bucket_summaries = dict(model["summary"].get("bucket_summaries", {}))
        for bucket, summary in bucket_summaries.items():
            lines.append(
                f"- {bucket}: pass_rate=`{summary['pass_rate']}`, "
                f"score=`{summary['avg_weighted_score']}`, "
                f"support=`{summary.get('support_pass_rate', 0.0)}`, "
                f"p95_ms=`{summary['p95_latency_ms']}`"
            )

    lines.extend(["", "## Gate Checks"])
    for model in report["models"]:
        lines.extend(["", f"### {model['label']}"])
        for check in model["gate"]["checks"]:
            status = "pass" if check["pass"] else "fail"
            lines.append(
                f"- {check['name']}: `{status}` actual=`{check['actual']}` expected=`{check['expected']}`"
            )

    lines.extend(["", "## Failed Or Weak Cases"])
    for model in report["models"]:
        lines.extend(["", f"### {model['label']}"])
        if not model["failed_cases"]:
            lines.append("- none")
            continue
        for case in model["failed_cases"]:
            answer_preview = str(case.get("answer_preview", "")).replace("`", "'")
            lines.extend(
                [
                    f"- {case['id']} ({case['bucket']}): pass=`{case['pass']}`, "
                    f"score=`{case['weighted_score']}`, latency_ms=`{case['latency_ms']}`",
                    f"  required_hits=`{case['required_hits']}`, "
                    f"any_hits=`{case['must_include_any_hits']}`, "
                    f"support=`{case['support_level']}`, citations=`{case['citation_count']}`, "
                    f"source_coverage=`{case['source_route_coverage_ratio']}`",
                    f"  answer_preview=`{answer_preview}`",
                ]
            )
    return "\n".join(lines) + "\n"


def write_outputs(report: dict[str, object], *, output_json: Path, output_report: Path) -> None:
    output_json = (ROOT_DIR / output_json).resolve() if not output_json.is_absolute() else output_json
    output_report = (ROOT_DIR / output_report).resolve() if not output_report.is_absolute() else output_report
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    output_report.parent.mkdir(parents=True, exist_ok=True)
    output_report.write_text(build_markdown_report(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compare RAG answer quality across model candidates.")
    parser.add_argument("--base-url", default=eval_query_quality.DEFAULT_BASE_URL)
    parser.add_argument("--timeout-seconds", type=int, default=eval_query_quality.DEFAULT_TIMEOUT_SECONDS)
    parser.add_argument("--eval-file", type=Path, default=eval_query_quality.DEFAULT_EVAL_FILE)
    parser.add_argument("--bucket", action="append", default=[])
    parser.add_argument("--required-bucket", action="append", default=[])
    parser.add_argument("--model", action="append", required=True)
    parser.add_argument("--llm-provider", default="ollama")
    parser.add_argument("--llm-base-url", default=None)
    parser.add_argument("--llm-api-key", default=None)
    parser.add_argument("--query-timeout-seconds", type=int, default=None)
    parser.add_argument("--quality-mode", choices=["balanced", "quality"], default=None)
    parser.add_argument("--quality-stage", default=None)
    parser.add_argument("--min-pass-rate", type=float, default=DEFAULT_MIN_PASS_RATE)
    parser.add_argument("--min-avg-weighted-score", type=float, default=DEFAULT_MIN_AVG_WEIGHTED_SCORE)
    parser.add_argument("--max-p95-ms", type=float, default=DEFAULT_MAX_P95_MS)
    parser.add_argument("--output-json", type=Path, default=DEFAULT_OUTPUT_JSON)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    selected_buckets = [item.strip() for item in args.bucket if item.strip()] or list(DEFAULT_BUCKETS)
    required_buckets = [item.strip() for item in args.required_bucket if item.strip()] or selected_buckets
    model_specs = [
        parse_model_spec(value, default_provider=args.llm_provider)
        for value in args.model
    ]

    payloads: list[dict[str, object]] = []
    for spec in model_specs:
        payloads.append(
            eval_query_quality.run_evaluation(
                backend="vector_query",
                base_url=args.base_url,
                timeout_seconds=args.timeout_seconds,
                eval_file=args.eval_file,
                buckets=set(selected_buckets),
                llm_provider=spec.provider,
                llm_model=spec.model,
                llm_base_url=args.llm_base_url,
                llm_api_key=args.llm_api_key,
                query_timeout_seconds=args.query_timeout_seconds,
                quality_mode=args.quality_mode,
                quality_stage=args.quality_stage,
                debug=True,
            )
        )

    report = build_report(
        model_payloads=payloads,
        required_buckets=required_buckets,
        min_pass_rate=args.min_pass_rate,
        min_avg_weighted_score=args.min_avg_weighted_score,
        max_p95_ms=args.max_p95_ms,
        selected_buckets=selected_buckets,
        eval_file=args.eval_file,
        base_url=args.base_url,
        timeout_seconds=args.timeout_seconds,
        query_timeout_seconds=args.query_timeout_seconds,
        quality_mode=args.quality_mode,
        quality_stage=args.quality_stage,
    )
    write_outputs(report, output_json=args.output_json, output_report=args.output_report)
    print(json.dumps({key: report[key] for key in ("outcome", "recommendation", "selected_candidate")}, ensure_ascii=False, indent=2))
    return 0 if report["outcome"] == "ready" else 1


if __name__ == "__main__":
    raise SystemExit(main())
