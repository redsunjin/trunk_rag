from __future__ import annotations

from pathlib import Path

from scripts import check_ops_baseline_gate


def test_build_gate_report_returns_blocked_when_app_health_is_unreachable(monkeypatch):
    def fake_runtime_report(**_: object) -> dict[str, object]:
        return {
            "ready": False,
            "checks": [
                {
                    "name": "app_health",
                    "ready": False,
                    "message": "health endpoint unreachable: <urlopen error [Errno 61] Connection refused>",
                }
            ],
        }

    monkeypatch.setattr(check_ops_baseline_gate.runtime_preflight, "build_report", fake_runtime_report)
    monkeypatch.setattr(check_ops_baseline_gate.runtime_service, "get_embedding_model", lambda: "BAAI/bge-m3")

    def fail_if_called(*args: object, **kwargs: object) -> None:
        raise AssertionError("collections_check should not run when app health is blocked")

    monkeypatch.setattr(check_ops_baseline_gate.eval_query_quality, "collections_check", fail_if_called)

    report = check_ops_baseline_gate.build_gate_report(
        base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
        eval_file=Path("evals/answer_level_eval_fixtures.jsonl"),
        llm_provider="ollama",
        llm_model="llama3.1:8b",
        llm_base_url="http://localhost:11434",
        llm_api_key=None,
    )

    assert report["ready"] is False
    assert report["diagnostics"][0]["code"] == "APP_HEALTH_UNREACHABLE"
    assert report["eval"]["summary"]["cases"] == 0
    assert report["eval"]["selected_buckets"] == ["generic-baseline"]
    assert report["runtime"]["checks"][0]["name"] == "app_health"


def test_build_gate_report_returns_blocked_when_eval_precondition_fails(monkeypatch):
    def fake_runtime_report(**_: object) -> dict[str, object]:
        return {
            "ready": True,
            "checks": [
                {
                    "name": "app_health",
                    "ready": True,
                    "message": "ready",
                    "payload": {"status": "ok", "vectors": 37},
                }
            ],
        }

    monkeypatch.setattr(check_ops_baseline_gate.runtime_preflight, "build_report", fake_runtime_report)
    monkeypatch.setattr(check_ops_baseline_gate.runtime_service, "get_embedding_model", lambda: "BAAI/bge-m3")
    monkeypatch.setattr(
        check_ops_baseline_gate.eval_query_quality,
        "collections_check",
        lambda *args, **kwargs: {
            "collections": [
                {"key": "all", "vectors": 37},
                {"key": "eu", "vectors": 9},
                {"key": "fr", "vectors": 7},
                {"key": "ge", "vectors": 7},
                {"key": "it", "vectors": 7},
                {"key": "uk", "vectors": 0},
            ]
        },
    )

    def raise_eval_error(*args: object, **kwargs: object) -> None:
        raise ValueError("Selected eval fixtures require empty collections. 먼저 /reindex 가 필요합니다: GQ-03: uk")

    monkeypatch.setattr(check_ops_baseline_gate.eval_query_quality, "run_evaluation", raise_eval_error)

    report = check_ops_baseline_gate.build_gate_report(
        base_url="http://127.0.0.1:8000",
        timeout_seconds=5,
        eval_file=Path("evals/answer_level_eval_fixtures.jsonl"),
        llm_provider="ollama",
        llm_model="llama3.1:8b",
        llm_base_url="http://localhost:11434",
        llm_api_key=None,
    )

    assert report["ready"] is False
    assert report["diagnostics"][0]["code"] == "OPS_EVAL_FAILED"
    assert report["collections"]["missing_keys"] == ["uk"]
    assert report["eval"]["summary"]["cases"] == 0
    assert report["eval"]["selected_buckets"] == ["generic-baseline"]
