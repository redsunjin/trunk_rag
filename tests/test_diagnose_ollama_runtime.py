from __future__ import annotations

from scripts import diagnose_ollama_runtime


def test_safe_tokens_per_second_returns_none_for_invalid_values():
    assert diagnose_ollama_runtime.safe_tokens_per_second(None, 10) is None
    assert diagnose_ollama_runtime.safe_tokens_per_second(10, 0) is None
    assert diagnose_ollama_runtime.safe_tokens_per_second(0, 10) is None


def test_safe_tokens_per_second_computes_expected_value():
    value = diagnose_ollama_runtime.safe_tokens_per_second(40, 2_000_000_000)

    assert value == 20.0


def test_summarize_runs_marks_slow_runtime():
    runs = [
        {
            "run": 1,
            "ok": True,
            "wall_ms": 18234.0,
            "eval_tokens_per_second": 5.4,
            "prompt_tokens_per_second": 80.0,
        },
        {
            "run": 2,
            "ok": True,
            "wall_ms": 17654.0,
            "eval_tokens_per_second": 5.9,
            "prompt_tokens_per_second": 82.0,
        },
    ]

    summary = diagnose_ollama_runtime.summarize_runs(runs)

    assert summary["success_count"] == 2
    assert summary["assessment"]["status"] == "slow"
    assert "timeout" in summary["assessment"]["message"]


def test_summarize_runs_marks_promising_runtime():
    runs = [
        {
            "run": 1,
            "ok": True,
            "wall_ms": 2200.0,
            "eval_tokens_per_second": 24.0,
            "prompt_tokens_per_second": 120.0,
        },
        {
            "run": 2,
            "ok": True,
            "wall_ms": 2100.0,
            "eval_tokens_per_second": 26.0,
            "prompt_tokens_per_second": 118.0,
        },
    ]

    summary = diagnose_ollama_runtime.summarize_runs(runs)

    assert summary["assessment"]["status"] == "promising"


def test_normalize_run_extracts_core_metrics():
    payload = {
        "done": True,
        "prompt_eval_count": 30,
        "prompt_eval_duration": 500_000_000,
        "eval_count": 20,
        "eval_duration": 2_000_000_000,
        "total_duration": 3_000_000_000,
        "message": {"content": "확인"},
    }

    run = diagnose_ollama_runtime.normalize_run(payload, wall_ms=3100.0, index=1)

    assert run["ok"] is True
    assert run["prompt_tokens_per_second"] == 60.0
    assert run["eval_tokens_per_second"] == 10.0
    assert run["response_preview"] == "확인"
