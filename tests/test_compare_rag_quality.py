from __future__ import annotations

from pathlib import Path

from scripts import compare_rag_quality


def test_parse_model_spec_accepts_provider_prefix_with_colon_model_name():
    spec = compare_rag_quality.parse_model_spec(
        "ollama:gemma4:e2b",
        default_provider="ollama",
    )

    assert spec.provider == "ollama"
    assert spec.model == "gemma4:e2b"
    assert spec.label == "ollama:gemma4:e2b"


def test_parse_model_spec_uses_default_provider_for_plain_model_name():
    spec = compare_rag_quality.parse_model_spec(
        "gemma4:e2b",
        default_provider="ollama",
    )

    assert spec.provider == "ollama"
    assert spec.model == "gemma4:e2b"


def test_evaluate_gate_blocks_when_required_bucket_fails():
    summary = {
        "pass_rate": 0.8333,
        "avg_weighted_score": 0.7962,
        "p95_latency_ms": 8648.43,
        "support_pass_rate": 1.0,
        "bucket_summaries": {
            "generic-baseline": {
                "pass_rate": 1.0,
                "avg_weighted_score": 0.92,
                "p95_latency_ms": 2212.647,
                "support_pass_rate": 1.0,
            },
            "sample-pack-baseline": {
                "pass_rate": 0.6667,
                "avg_weighted_score": 0.6724,
                "p95_latency_ms": 9921.998,
                "support_pass_rate": 1.0,
            },
        },
    }

    gate = compare_rag_quality.evaluate_gate(
        summary,
        required_buckets=["generic-baseline", "sample-pack-baseline"],
        min_pass_rate=1.0,
        min_avg_weighted_score=0.85,
        max_p95_ms=20_000.0,
    )

    assert gate["ready"] is False
    assert any(
        check["name"] == "sample-pack-baseline.pass_rate" and check["pass"] is False
        for check in gate["checks"]
    )


def test_build_report_selects_strongest_candidate_but_blocks_without_gate_ready():
    payload = {
        "llm_provider": "ollama",
        "llm_model": "gemma4:e2b",
        "summary": {
            "cases": 1,
            "passed": 0,
            "pass_rate": 0.0,
            "avg_weighted_score": 0.5,
            "p95_latency_ms": 1000.0,
            "support_pass_rate": 1.0,
            "bucket_summaries": {
                "generic-baseline": {
                    "pass_rate": 0.0,
                    "avg_weighted_score": 0.5,
                    "p95_latency_ms": 1000.0,
                    "support_pass_rate": 1.0,
                }
            },
        },
        "results": [
            {
                "id": "GQ-19",
                "bucket": "generic-baseline",
                "pass": False,
                "support_pass": True,
                "weighted_score": 0.5,
                "latency_ms": 1000.0,
                "required_hits": [],
                "required_total": 2,
                "must_include_any_hits": [],
                "must_include_any_total": 5,
                "support_level": "supported",
                "citation_count": 1,
                "source_route_coverage_ratio": 1.0,
                "answer_preview": "sample",
            }
        ],
    }

    report = compare_rag_quality.build_report(
        model_payloads=[payload],
        required_buckets=["generic-baseline"],
        min_pass_rate=1.0,
        min_avg_weighted_score=0.85,
        max_p95_ms=20_000.0,
        selected_buckets=["generic-baseline"],
        eval_file=Path("evals/answer_level_eval_fixtures.jsonl"),
        base_url="http://127.0.0.1:8000",
        timeout_seconds=45,
    )

    assert report["outcome"] == "blocked"
    assert report["selected_candidate"] == "ollama:gemma4:e2b"
