from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from core.settings import DEFAULT_COLLECTION_KEY

DEFAULT_FEEDBACK_FILE = Path("chroma_db/query_feedback.jsonl")
DEFAULT_OUTPUT_JSONL = Path("docs/reports/query_feedback_fixture_candidates_latest.jsonl")
DEFAULT_OUTPUT_REPORT = Path("docs/reports/QUERY_FEEDBACK_FIXTURE_CANDIDATES_LATEST.md")
REVIEW_RATINGS = {"negative", "quality_request"}
DEFAULT_SCORE_WEIGHTS = {"precision": 0.5, "completeness": 0.4, "hallucination": 0.1}
DEFAULT_MUST_NOT_INCLUDE = ["근거 없음", "정보 부족", "확인되지 않습니다", "판단 불가"]


def _resolve_repo_path(path: Path) -> Path:
    return path if path.is_absolute() else ROOT_DIR / path


def _stable_hash(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()[:10].upper()


def _string_list(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item).strip() for item in value if str(item).strip()]


def load_feedback_records(path: Path) -> list[dict[str, Any]]:
    resolved = _resolve_repo_path(path)
    if not resolved.exists():
        return []
    records: list[dict[str, Any]] = []
    with resolved.open(encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"invalid feedback JSON at {resolved}:{line_no}") from exc
            if not isinstance(record, dict):
                raise ValueError(f"feedback record must be an object at {resolved}:{line_no}")
            record["_line_no"] = line_no
            records.append(record)
    return records


def normalize_collection_keys(record: dict[str, Any]) -> list[str]:
    collections = _string_list(record.get("collections"))
    if not collections and isinstance(record.get("meta"), dict):
        collections = _string_list(record["meta"].get("collections"))
    return collections or [DEFAULT_COLLECTION_KEY]


def infer_query_profile(record: dict[str, Any], collection_keys: list[str]) -> str:
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    query_profile = str(meta.get("query_profile", "") or "").strip()
    if query_profile:
        return query_profile
    if any(key != DEFAULT_COLLECTION_KEY for key in collection_keys):
        return "sample_pack"
    return "generic"


def infer_relation_shape(query: str, collection_keys: list[str]) -> str:
    if len(collection_keys) > 1:
        return "feedback -> multi-collection comparison"
    if any(term in query for term in ["비교", "차이", "대조"]):
        return "feedback -> comparison"
    if any(term in query for term in ["요약", "정리"]):
        return "feedback -> summary"
    return "feedback -> question"


def classify_priority(record: dict[str, Any]) -> str:
    rating = str(record.get("rating", "") or "").strip()
    reason_tags = set(_string_list(record.get("reason_tags")))
    if rating == "negative":
        return "high"
    if "manual_quality" in reason_tags or rating == "quality_request":
        return "medium"
    return "low"


def include_record(record: dict[str, Any], *, include_positive: bool) -> bool:
    rating = str(record.get("rating", "") or "").strip()
    if rating in REVIEW_RATINGS:
        return True
    return include_positive and rating == "positive"


def build_candidate(record: dict[str, Any], *, source_path: Path, index: int) -> dict[str, Any] | None:
    query = str(record.get("query", "") or "").strip()
    if not query:
        return None
    collection_keys = normalize_collection_keys(record)
    answer = str(record.get("answer", "") or "")
    meta = record.get("meta") if isinstance(record.get("meta"), dict) else {}
    reason_tags = _string_list(record.get("reason_tags"))
    feedback_id = str(record.get("id") or record.get("feedback_id") or "").strip()
    request_id = str(record.get("request_id") or "").strip()
    candidate_seed = "|".join([feedback_id, request_id, query, ",".join(collection_keys), str(index)])
    candidate_id = f"FB-{_stable_hash(candidate_seed)}"

    min_answer_chars = max(80, min(220, len(answer.strip()) if answer.strip() else 120))
    query_profile = infer_query_profile(record, collection_keys)
    return {
        "format_version": "feedback-candidate/v1",
        "id": candidate_id,
        "status": "needs_fixture_review",
        "priority": classify_priority(record),
        "bucket": "feedback-candidate",
        "query_profile": query_profile,
        "collection_keys": collection_keys,
        "relation_shape": infer_relation_shape(query, collection_keys),
        "query": query,
        "observed_answer": answer,
        "source_feedback": {
            "feedback_id": feedback_id or "-",
            "request_id": request_id or "-",
            "created_at": str(record.get("created_at") or "-"),
            "rating": str(record.get("rating") or "-"),
            "reason_tags": reason_tags,
            "line_no": record.get("_line_no"),
            "source": str(source_path),
        },
        "observed_runtime": {
            "quality_mode": str(record.get("quality_mode") or "-"),
            "quality_stage": str(record.get("quality_stage") or "-"),
            "provider": str(record.get("provider") or "-"),
            "model": str(record.get("model") or "-"),
            "support_level": str(meta.get("support_level") or "-"),
            "support_reason": str(meta.get("support_reason") or "-"),
            "citations": _string_list(meta.get("citations")),
        },
        "suggested_fixture": {
            "format_version": "1.0",
            "id": candidate_id,
            "bucket": "feedback-candidate",
            "query_profile": query_profile,
            "collection_keys": collection_keys,
            "relation_shape": infer_relation_shape(query, collection_keys),
            "query": query,
            "evaluation": {
                "min_answer_chars": min_answer_chars,
                "must_include": [],
                "must_not_include": DEFAULT_MUST_NOT_INCLUDE,
                "must_include_any": [],
                "source": "chroma_db/query_feedback.jsonl",
                "score_weights": DEFAULT_SCORE_WEIGHTS,
            },
        },
    }


def dedupe_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_key: dict[tuple[str, tuple[str, ...]], dict[str, Any]] = {}
    priority_rank = {"low": 0, "medium": 1, "high": 2}
    for candidate in candidates:
        key = (
            str(candidate["query"]).strip().lower(),
            tuple(str(item) for item in candidate.get("collection_keys", [])),
        )
        previous = by_key.get(key)
        if previous is None:
            by_key[key] = candidate
            continue
        previous_rank = priority_rank.get(str(previous.get("priority")), 0)
        candidate_rank = priority_rank.get(str(candidate.get("priority")), 0)
        if candidate_rank >= previous_rank:
            by_key[key] = candidate
    return list(by_key.values())


def build_candidates(
    records: list[dict[str, Any]],
    *,
    source_path: Path,
    include_positive: bool = False,
    dedupe: bool = True,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for index, record in enumerate(records, start=1):
        if not include_record(record, include_positive=include_positive):
            continue
        candidate = build_candidate(record, source_path=source_path, index=index)
        if candidate:
            candidates.append(candidate)
    return dedupe_candidates(candidates) if dedupe else candidates


def summarize(records: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "feedback_records": len(records),
        "candidates": len(candidates),
        "rating_counts": dict(Counter(str(item.get("rating") or "-") for item in records)),
        "candidate_priority_counts": dict(Counter(str(item.get("priority") or "-") for item in candidates)),
        "candidate_bucket_counts": dict(Counter(str(item.get("bucket") or "-") for item in candidates)),
    }


def build_payload(
    *,
    feedback_file: Path,
    records: list[dict[str, Any]],
    candidates: list[dict[str, Any]],
    include_positive: bool,
    dedupe: bool,
) -> dict[str, Any]:
    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "feedback_file": str(feedback_file),
        "include_positive": include_positive,
        "dedupe": dedupe,
        "summary": summarize(records, candidates),
        "candidates": candidates,
    }


def build_markdown_report(payload: dict[str, Any]) -> str:
    summary = payload["summary"]
    lines = [
        "# Query Feedback Fixture Candidates",
        "",
        "## Scope",
        f"- generated_at: `{payload['generated_at']}`",
        f"- feedback_file: `{payload['feedback_file']}`",
        f"- include_positive: `{payload['include_positive']}`",
        f"- dedupe: `{payload['dedupe']}`",
        "",
        "## Summary",
        f"- feedback_records: `{summary['feedback_records']}`",
        f"- candidates: `{summary['candidates']}`",
        f"- rating_counts: `{summary['rating_counts']}`",
        f"- candidate_priority_counts: `{summary['candidate_priority_counts']}`",
        "",
        "## Candidate Queue",
    ]
    if not payload["candidates"]:
        lines.append("- 후보가 없습니다. `/app` 답변 피드백이 쌓인 뒤 다시 실행하세요.")
        return "\n".join(lines) + "\n"

    for candidate in payload["candidates"]:
        source = candidate["source_feedback"]
        runtime = candidate["observed_runtime"]
        lines.extend(
            [
                f"### {candidate['id']}",
                f"- priority: `{candidate['priority']}`",
                f"- rating: `{source['rating']}`",
                f"- reason_tags: `{', '.join(source['reason_tags']) or '-'}`",
                f"- query_profile: `{candidate['query_profile']}`",
                f"- collection_keys: `{', '.join(candidate['collection_keys'])}`",
                f"- quality: `{runtime['quality_mode']}` / `{runtime['quality_stage']}`",
                f"- model: `{runtime['provider']}:{runtime['model']}`",
                f"- query: {candidate['query']}",
                f"- next: `suggested_fixture.evaluation.must_include`와 `must_include_any`를 채운 뒤 answer-level fixture로 승격",
            ]
        )
    return "\n".join(lines) + "\n"


def write_outputs(payload: dict[str, Any], *, output_jsonl: Path, output_report: Path) -> None:
    resolved_jsonl = _resolve_repo_path(output_jsonl)
    resolved_report = _resolve_repo_path(output_report)
    resolved_jsonl.parent.mkdir(parents=True, exist_ok=True)
    resolved_report.parent.mkdir(parents=True, exist_ok=True)
    with resolved_jsonl.open("w", encoding="utf-8") as handle:
        for candidate in payload["candidates"]:
            handle.write(json.dumps(candidate, ensure_ascii=False, sort_keys=True) + "\n")
    resolved_report.write_text(build_markdown_report(payload), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export /query-feedback records into reviewable eval fixture candidates.")
    parser.add_argument("--feedback-file", type=Path, default=DEFAULT_FEEDBACK_FILE)
    parser.add_argument("--output-jsonl", type=Path, default=DEFAULT_OUTPUT_JSONL)
    parser.add_argument("--output-report", type=Path, default=DEFAULT_OUTPUT_REPORT)
    parser.add_argument("--include-positive", action="store_true")
    parser.add_argument("--no-dedupe", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    records = load_feedback_records(args.feedback_file)
    candidates = build_candidates(
        records,
        source_path=args.feedback_file,
        include_positive=args.include_positive,
        dedupe=not args.no_dedupe,
    )
    payload = build_payload(
        feedback_file=args.feedback_file,
        records=records,
        candidates=candidates,
        include_positive=args.include_positive,
        dedupe=not args.no_dedupe,
    )
    write_outputs(payload, output_jsonl=args.output_jsonl, output_report=args.output_report)
    print(
        "feedback_fixture_candidates "
        f"records={payload['summary']['feedback_records']} "
        f"candidates={payload['summary']['candidates']} "
        f"output_jsonl={args.output_jsonl} output_report={args.output_report}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
