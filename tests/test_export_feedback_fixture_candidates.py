from __future__ import annotations

import json
from pathlib import Path

from scripts import export_feedback_fixture_candidates as exporter


def test_build_candidates_exports_negative_feedback_as_review_item(tmp_path):
    feedback_file = Path("chroma_db/query_feedback.jsonl")
    records = [
        {
            "id": "feedback-1",
            "created_at": "2026-04-28T00:00:00Z",
            "request_id": "req-1",
            "query": "프랑스와 독일의 인재 양성을 비교해줘.",
            "answer": "제공된 문서에서 확인되지 않습니다.",
            "rating": "negative",
            "reason_tags": ["needs_better_answer"],
            "quality_mode": "balanced",
            "quality_stage": "fast",
            "provider": "ollama",
            "model": "gemma4:e2b",
            "collections": ["fr", "ge"],
            "meta": {
                "query_profile": "sample_pack",
                "support_level": "supported",
                "support_reason": "multiple_context_segments",
                "citations": ["fr.md", "ge.md"],
            },
        }
    ]

    candidates = exporter.build_candidates(records, source_path=feedback_file)

    assert len(candidates) == 1
    candidate = candidates[0]
    assert candidate["id"].startswith("FB-")
    assert candidate["priority"] == "high"
    assert candidate["query_profile"] == "sample_pack"
    assert candidate["collection_keys"] == ["fr", "ge"]
    assert candidate["suggested_fixture"]["evaluation"]["must_include"] == []
    assert "확인되지 않습니다" in candidate["suggested_fixture"]["evaluation"]["must_not_include"]


def test_build_candidates_skips_positive_by_default_and_can_include_it():
    records = [
        {
            "id": "feedback-1",
            "query": "좋은 답변이었나요?",
            "answer": "좋은 답변입니다.",
            "rating": "positive",
            "collections": ["all"],
        }
    ]

    assert exporter.build_candidates(records, source_path=Path("feedback.jsonl")) == []

    candidates = exporter.build_candidates(
        records,
        source_path=Path("feedback.jsonl"),
        include_positive=True,
    )
    assert len(candidates) == 1
    assert candidates[0]["priority"] == "low"
    assert candidates[0]["query_profile"] == "generic"


def test_dedupe_keeps_higher_priority_for_same_query_and_collections():
    records = [
        {
            "id": "feedback-positive",
            "query": "같은 질문",
            "answer": "답변",
            "rating": "positive",
            "collections": ["all"],
        },
        {
            "id": "feedback-negative",
            "query": "같은 질문",
            "answer": "부족한 답변",
            "rating": "negative",
            "collections": ["all"],
        },
    ]

    candidates = exporter.build_candidates(
        records,
        source_path=Path("feedback.jsonl"),
        include_positive=True,
    )

    assert len(candidates) == 1
    assert candidates[0]["source_feedback"]["feedback_id"] == "feedback-negative"
    assert candidates[0]["priority"] == "high"


def test_write_outputs_creates_jsonl_and_report(tmp_path):
    payload = exporter.build_payload(
        feedback_file=Path("feedback.jsonl"),
        records=[],
        candidates=[],
        include_positive=False,
        dedupe=True,
    )
    output_jsonl = tmp_path / "candidates.jsonl"
    output_report = tmp_path / "report.md"

    exporter.write_outputs(payload, output_jsonl=output_jsonl, output_report=output_report)

    assert output_jsonl.exists()
    assert output_jsonl.read_text(encoding="utf-8") == ""
    assert "후보가 없습니다" in output_report.read_text(encoding="utf-8")


def test_load_feedback_records_rejects_invalid_json(tmp_path):
    feedback_file = tmp_path / "feedback.jsonl"
    feedback_file.write_text("{bad json}\n", encoding="utf-8")

    try:
        exporter.load_feedback_records(feedback_file)
    except ValueError as exc:
        assert "invalid feedback JSON" in str(exc)
    else:
        raise AssertionError("expected invalid JSON to raise")


def test_load_feedback_records_reads_jsonl(tmp_path):
    feedback_file = tmp_path / "feedback.jsonl"
    feedback_file.write_text(json.dumps({"query": "테스트", "rating": "negative"}, ensure_ascii=False) + "\n", encoding="utf-8")

    records = exporter.load_feedback_records(feedback_file)

    assert records[0]["query"] == "테스트"
    assert records[0]["_line_no"] == 1
