from __future__ import annotations

from pathlib import Path

from scripts import check_ops_baseline_gate


def test_summarize_collection_vectors_reports_missing_route():
    payload = {
        "collections": [
            {"key": "all", "vectors": 37},
            {"key": "fr", "vectors": 7},
        ]
    }

    result = check_ops_baseline_gate.summarize_collection_vectors(
        payload,
        required_keys=["all", "fr", "uk"],
    )

    assert result["ready"] is False
    assert result["missing_keys"] == ["uk"]
    assert result["items"][-1] == {"key": "uk", "vectors": 0, "ready": False}


def test_evaluate_gate_ready_requires_full_eval_pass_and_collections():
    assert (
        check_ops_baseline_gate.evaluate_gate_ready(
            collection_summary={"ready": True},
            eval_summary={"cases": 3, "passed": 3, "pass_rate": 1.0},
        )
        is True
    )
    assert (
        check_ops_baseline_gate.evaluate_gate_ready(
            collection_summary={"ready": False},
            eval_summary={"cases": 3, "passed": 3, "pass_rate": 1.0},
        )
        is False
    )
    assert (
        check_ops_baseline_gate.evaluate_gate_ready(
            collection_summary={"ready": True},
            eval_summary={"cases": 3, "passed": 2, "pass_rate": 0.6667},
        )
        is False
    )


def test_build_gate_report_uses_eval_summary_and_collection_state(monkeypatch):
    monkeypatch.setattr(
        check_ops_baseline_gate.eval_query_quality,
        "collections_check",
        lambda base_url, timeout_seconds: {
            "collections": [
                {"key": "all", "vectors": 37},
                {"key": "eu", "vectors": 9},
                {"key": "fr", "vectors": 7},
                {"key": "ge", "vectors": 7},
                {"key": "it", "vectors": 7},
                {"key": "uk", "vectors": 7},
            ]
        },
    )
    monkeypatch.setattr(
        check_ops_baseline_gate.eval_query_quality,
        "run_evaluation",
        lambda **kwargs: {
            "health": {"status": "ok", "vectors": 37},
            "summary": {
                "cases": 3,
                "passed": 3,
                "pass_rate": 1.0,
                "avg_weighted_score": 0.9645,
                "avg_latency_ms": 6095.881,
                "p95_latency_ms": 8724.427,
            },
            "results": [{"id": "GQ-01", "pass": True}],
        },
    )

    report = check_ops_baseline_gate.build_gate_report(
        base_url="http://127.0.0.1:8000",
        timeout_seconds=45,
        eval_file=Path("evals/answer_level_eval_fixtures.jsonl"),
        llm_provider="ollama",
        llm_model="llama3.1:8b",
        llm_base_url="http://localhost:11434",
        llm_api_key=None,
    )

    assert report["ready"] is True
    assert report["collections"]["ready"] is True
    assert report["eval"]["summary"]["pass_rate"] == 1.0
