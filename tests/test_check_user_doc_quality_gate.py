from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from scripts import check_user_doc_quality_gate

EXPECTED_USER_DOC_CASE_IDS = {"UDQ-BC-01", "UDQ-BC-02", "UDQ-BC-03"}


def _ready_runtime_report() -> dict[str, object]:
    return {
        "ready": True,
        "checks": [
            {
                "name": "app_health",
                "ready": True,
                "message": "ready",
                "payload": {"status": "ok", "vectors": 10},
            }
        ],
    }


def test_build_gate_report_blocks_when_project_docs_vectors_are_missing(monkeypatch):
    monkeypatch.setattr(
        check_user_doc_quality_gate.runtime_preflight,
        "build_report",
        lambda **_: _ready_runtime_report(),
    )
    monkeypatch.setattr(
        check_user_doc_quality_gate.runtime_service,
        "get_embedding_model",
        lambda: "BAAI/bge-m3",
    )
    monkeypatch.setattr(
        check_user_doc_quality_gate.eval_query_quality,
        "collections_check",
        lambda *args, **kwargs: {
            "collections": [
                {"key": "all", "vectors": 37},
                {"key": "project_docs", "vectors": 0},
            ]
        },
    )

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("user-doc eval should not run before project_docs is indexed")

    monkeypatch.setattr(check_user_doc_quality_gate.eval_query_quality, "run_evaluation", fail_if_called)

    report = check_user_doc_quality_gate.build_gate_report(
        base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
        eval_file=Path("evals/user_doc_answer_level_eval_fixtures.jsonl"),
        buckets={"user-doc-candidate"},
        case_ids=EXPECTED_USER_DOC_CASE_IDS,
        llm_provider="ollama",
        llm_model="gemma4:e4b",
        llm_base_url="http://localhost:11434",
        llm_api_key=None,
        query_timeout_seconds=60,
    )

    assert report["ready"] is False
    assert report["diagnostics"][0]["code"] == "PROJECT_DOCS_REINDEX_REQUIRED"
    assert "project_docs" in report["diagnostics"][0]["hint"]
    assert "reindex_single_collection" in report["diagnostics"][0]["hint"]
    assert report["collections"]["missing_keys"] == ["project_docs"]
    assert report["eval"]["selected_buckets"] == ["user-doc-candidate"]
    assert report["eval"]["selected_case_ids"] == sorted(EXPECTED_USER_DOC_CASE_IDS)
    assert report["boundary"]["default_release_gate"] == "generic-baseline"
    assert report["boundary"]["default_runtime_collection_changed"] is False


def test_build_gate_report_runs_udq_case_with_user_doc_fixture(monkeypatch):
    monkeypatch.setattr(
        check_user_doc_quality_gate.runtime_preflight,
        "build_report",
        lambda **_: _ready_runtime_report(),
    )
    monkeypatch.setattr(
        check_user_doc_quality_gate.runtime_service,
        "get_embedding_model",
        lambda: "BAAI/bge-m3",
    )
    monkeypatch.setattr(
        check_user_doc_quality_gate.eval_query_quality,
        "collections_check",
        lambda *args, **kwargs: {"collections": [{"key": "project_docs", "vectors": 10}]},
    )

    calls: list[dict[str, object]] = []

    def fake_run_evaluation(**kwargs: object) -> dict[str, object]:
        calls.append(kwargs)
        return {
            "health": {"status": "ok"},
            "results": [{"id": case_id, "pass": True} for case_id in sorted(EXPECTED_USER_DOC_CASE_IDS)],
            "summary": {
                "cases": 3,
                "passed": 3,
                "pass_rate": 1.0,
                "avg_latency_ms": 1200.0,
                "p95_latency_ms": 1200.0,
                "avg_weighted_score": 1.0,
                "support_pass_rate": 1.0,
                "source_route_pass_rate": 1.0,
                "bucket_summaries": {},
            },
        }

    monkeypatch.setattr(check_user_doc_quality_gate.eval_query_quality, "run_evaluation", fake_run_evaluation)

    report = check_user_doc_quality_gate.build_gate_report(
        base_url="http://127.0.0.1:8000",
        timeout_seconds=90,
        eval_file=Path("evals/user_doc_answer_level_eval_fixtures.jsonl"),
        buckets={"user-doc-candidate"},
        case_ids=EXPECTED_USER_DOC_CASE_IDS,
        llm_provider="ollama",
        llm_model="gemma4:e4b",
        llm_base_url="http://localhost:11434",
        llm_api_key=None,
        query_timeout_seconds=60,
    )

    assert report["ready"] is True
    assert report["eval"]["summary"]["pass_rate"] == 1.0
    assert calls[0]["eval_file"] == Path("evals/user_doc_answer_level_eval_fixtures.jsonl")
    assert calls[0]["buckets"] == {"user-doc-candidate"}
    assert calls[0]["case_ids"] == EXPECTED_USER_DOC_CASE_IDS
    assert calls[0]["query_timeout_seconds"] == 60
    assert calls[0]["debug"] is True


def test_evaluate_gate_ready_requires_support_and_source_route_pass_rates():
    collection_summary = {
        "ready": True,
        "missing_keys": [],
        "items": [{"key": "project_docs", "vectors": 10, "ready": True}],
    }
    eval_summary = {
        "cases": 1,
        "passed": 1,
        "pass_rate": 1.0,
        "support_pass_rate": 1.0,
        "source_route_pass_rate": 0.0,
    }

    assert (
        check_user_doc_quality_gate.evaluate_gate_ready(
            runtime_ready=True,
            collection_summary=collection_summary,
            eval_summary=eval_summary,
        )
        is False
    )


def test_default_gate_case_ids_cover_user_doc_fixture_expansion():
    assert check_user_doc_quality_gate.DEFAULT_GATE_CASE_IDS == EXPECTED_USER_DOC_CASE_IDS


def test_latest_artifact_freshness_blocks_stale_ready_report():
    freshness = check_user_doc_quality_gate.evaluate_latest_artifact_freshness(
        {
            "generated_at": "2026-05-11T00:00:00+00:00",
            "ready": True,
        },
        artifact_path=Path("docs/reports/user_doc_quality_gate_latest.json"),
        now=datetime(2026, 5, 18, 1, 0, tzinfo=timezone.utc),
        max_age_hours=168,
    )

    assert freshness["ready"] is False
    assert freshness["fresh"] is False
    assert freshness["source_ready"] is True
    assert freshness["age_hours"] == 169.0
    assert freshness["expires_at"] == "2026-05-18T00:00:00+00:00"
    assert freshness["diagnostics"][0]["code"] == "USER_DOC_GATE_ARTIFACT_STALE"


def test_latest_artifact_freshness_keeps_recent_ready_report():
    freshness = check_user_doc_quality_gate.evaluate_latest_artifact_freshness(
        {
            "generated_at": "2026-05-11T00:00:00+00:00",
            "ready": True,
        },
        artifact_path=Path("docs/reports/user_doc_quality_gate_latest.json"),
        now=datetime(2026, 5, 17, 23, 59, tzinfo=timezone.utc),
        max_age_hours=168,
    )

    assert freshness["ready"] is True
    assert freshness["fresh"] is True
    assert freshness["source_ready"] is True
    assert freshness["diagnostics"] == []


def test_build_latest_artifact_freshness_report_reads_artifact(tmp_path):
    artifact_path = tmp_path / "user_doc_quality_gate_latest.json"
    artifact_path.write_text(
        '{"generated_at": "2026-05-11T00:00:00+00:00", "ready": true}',
        encoding="utf-8",
    )

    report = check_user_doc_quality_gate.build_latest_artifact_freshness_report(
        artifact_path=artifact_path,
        now=datetime(2026, 5, 18, 1, 0, tzinfo=timezone.utc),
        max_age_hours=168,
    )

    assert report["mode"] == "latest_artifact_freshness"
    assert report["ready"] is False
    assert report["latest_artifact"]["path"] == str(artifact_path)
    assert report["latest_artifact"]["diagnostics"][0]["code"] == "USER_DOC_GATE_ARTIFACT_STALE"
