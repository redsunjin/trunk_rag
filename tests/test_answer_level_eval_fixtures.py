from __future__ import annotations

import json
import re
from pathlib import Path

from json import JSONDecodeError

ROOT_DIR = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT_DIR / "evals" / "answer_level_eval_fixtures.jsonl"
QUESTION_SET_PATH = ROOT_DIR / "docs" / "GRAPH_RAG_QUESTION_SET.md"

REQUIRED_TOP_KEYS = {
    "format_version",
    "id",
    "bucket",
    "collection_keys",
    "relation_shape",
    "query",
    "evaluation",
}
REQUIRED_BUCKETS = {"ops-baseline", "graph-candidate"}
REQUIRED_EVAL_KEYS = {
    "min_answer_chars",
    "must_include",
    "must_not_include",
}


def _load_graph_rag_question_set() -> dict[str, dict[str, object]]:
    questions: dict[str, dict[str, object]] = {}
    with QUESTION_SET_PATH.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.strip()
            if not line.startswith("| GQ-"):
                continue
            if line.startswith("| ---"):
                continue
            parts = [part.strip() for part in line.strip("|").split("|")]
            if len(parts) < 5:
                continue
            question_id = parts[0]
            if not re.fullmatch(r"GQ-\d{2}", question_id):
                continue
            bucket = parts[1]
            collection_text = parts[2].strip("`")
            collection_keys = [item.strip() for item in collection_text.split(",") if item.strip()]
            relation_shape = parts[3]
            query = parts[4].strip()
            questions[question_id] = {
                "bucket": bucket,
                "collection_keys": collection_keys,
                "relation_shape": relation_shape,
                "query": query,
            }
    return questions


def _load_fixtures() -> list[dict[str, object]]:
    if not FIXTURE_PATH.exists():
        raise AssertionError(f"fixture file missing: {FIXTURE_PATH}")
    records: list[dict[str, object]] = []
    with FIXTURE_PATH.open(encoding="utf-8") as handle:
        for line_no, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except JSONDecodeError as exc:
                raise AssertionError(f"invalid JSON on line {line_no}: {line}") from exc
            assert isinstance(record, dict), f"line {line_no} is not an object"
            record["_line_no"] = line_no
            records.append(record)
    return records


def _is_float(value: object) -> bool:
    return isinstance(value, (int, float))


def test_fixture_records_are_loadable_and_complete():
    records = _load_fixtures()
    assert records, "fixture 파일이 비어있으면 안 됩니다."
    question_set = _load_graph_rag_question_set()
    ids: set[str] = set()

    for record in records:
        line_no = int(record.pop("_line_no", 0))
        for key in REQUIRED_TOP_KEYS:
            assert key in record, f"line {line_no}: missing key '{key}'"
        assert record["format_version"] == "1.0", f"line {line_no}: format_version은 1.0이어야 합니다."

        qid = record["id"]
        assert isinstance(qid, str) and qid in question_set, f"line {line_no}: {qid} is not in question set"
        assert qid not in ids, f"line {line_no}: duplicated id {qid}"
        ids.add(qid)

        bucket = record["bucket"]
        assert isinstance(bucket, str) and bucket in REQUIRED_BUCKETS, f"line {line_no}: invalid bucket"

        eval_block = record["evaluation"]
        assert isinstance(eval_block, dict), f"line {line_no}: evaluation should be dict"
        for key in REQUIRED_EVAL_KEYS:
            assert key in eval_block, f"line {line_no}: missing evaluation key '{key}'"

        collection_keys = record["collection_keys"]
        assert isinstance(collection_keys, list) and collection_keys, f"line {line_no}: collection_keys empty"
        assert all(isinstance(item, str) and item for item in collection_keys), (
            f"line {line_no}: collection_keys는 문자열 목록이어야 합니다."
        )

        source_record = question_set[qid]
        assert record["query"] == source_record["query"], (
            f"line {line_no}: question text should match docs/GRAPH_RAG_QUESTION_SET.md"
        )
        assert bucket == source_record["bucket"], f"line {line_no}: bucket should match source"
        assert set(collection_keys) == set(source_record["collection_keys"]), (
            f"line {line_no}: collection_keys should match source"
        )
        assert record["relation_shape"] == source_record["relation_shape"], (
            f"line {line_no}: relation_shape should match source"
        )

        min_chars = eval_block["min_answer_chars"]
        assert isinstance(min_chars, int) and min_chars >= 80, (
            f"line {line_no}: min_answer_chars should be >= 80"
        )
        must_include = eval_block["must_include"]
        assert isinstance(must_include, list) and must_include, f"line {line_no}: must_include empty"
        assert all(isinstance(item, str) and item for item in must_include), (
            f"line {line_no}: must_include only accepts non-empty strings"
        )

        must_not = eval_block["must_not_include"]
        assert isinstance(must_not, list) and all(isinstance(item, str) for item in must_not), (
            f"line {line_no}: must_not_include type invalid"
        )

        must_include_any = eval_block.get("must_include_any", [])
        assert isinstance(must_include_any, list), f"line {line_no}: must_include_any must be list"
        assert all(isinstance(item, str) and item for item in must_include_any), (
            f"line {line_no}: must_include_any should be strings"
        )

        score_weights = eval_block.get("score_weights", {})
        assert isinstance(score_weights, dict) and score_weights, f"line {line_no}: score_weights required"
        for name in ("precision", "completeness", "hallucination"):
            assert name in score_weights, f"line {line_no}: score_weights missing '{name}'"
            value = score_weights[name]
            assert _is_float(value) and 0.0 <= float(value) <= 1.0, (
                f"line {line_no}: score_weights.{name} should be 0.0~1.0"
            )
        assert score_weights["precision"] > 0, f"line {line_no}: precision weight should be > 0"
        assert score_weights["completeness"] > 0, f"line {line_no}: completeness weight should be > 0"


def test_fixture_coverage_with_question_set():
    records = _load_fixtures()
    question_set = _load_graph_rag_question_set()
    buckets = {record["bucket"] for record in records}
    assert "ops-baseline" in buckets, "ops-baseline 항목이 최소 1개 필요합니다."
    assert "graph-candidate" in buckets, "graph-candidate 항목이 최소 1개 필요합니다."
    assert "ops-baseline" in {
        record["bucket"] for record in records
    } and "graph-candidate" in {record["bucket"] for record in records}
    assert {record["id"] for record in records} <= set(question_set.keys())
