from __future__ import annotations

from scripts import eval_query_quality


def test_prepare_query_request_uses_default_all_for_more_than_two_collections():
    case = {
        "id": "GQ-15",
        "query": "sample",
        "collection_keys": ["fr", "ge", "uk", "it"],
    }

    payload, expected_route_keys, request_mode = eval_query_quality.prepare_query_request(case)

    assert payload["collection"] == "all"
    assert "collections" not in payload
    assert expected_route_keys == ["all"]
    assert request_mode == "fallback_all_for_eval"


def test_prepare_query_request_allows_three_collections_for_graph_snapshot_backend():
    case = {
        "id": "GQ-09",
        "query": "sample",
        "collection_keys": ["uk", "ge", "fr"],
    }

    payload, expected_route_keys, request_mode = eval_query_quality.prepare_query_request_for_backend(
        case,
        max_collection_keys=3,
    )

    assert payload["collection"] == "uk"
    assert payload["collections"] == ["uk", "ge", "fr"]
    assert expected_route_keys == ["uk", "ge", "fr"]
    assert request_mode == "explicit_multi"


def test_evaluate_case_result_marks_pass_when_required_terms_and_route_match():
    case = {
        "id": "GQ-01",
        "bucket": "sample-pack-baseline",
        "query": "에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘.",
        "collection_keys": ["fr"],
        "evaluation": {
            "min_answer_chars": 20,
            "must_include": ["에콜 폴리테크니크", "프랑스", "인재"],
            "must_not_include": ["근거 없음"],
            "must_include_any": ["교육", "양성"],
            "score_weights": {
                "precision": 0.5,
                "completeness": 0.4,
                "hallucination": 0.1,
            },
        },
    }
    body = {
        "answer": "에콜 폴리테크니크는 프랑스가 국가 주도로 과학 인재를 교육하고 양성한 핵심 기관이다."
    }
    headers = {"X-RAG-Collections": "rag_science_history_fr"}

    result = eval_query_quality.evaluate_case_result(
        case,
        status=200,
        body=body,
        headers=headers,
        latency_ms=123.4,
        expected_route_keys=["fr"],
        request_mode="explicit_single",
    )

    assert result["pass"] is True
    assert result["route_pass"] is True
    assert result["required_ratio"] == 1.0
    assert result["must_include_any_ratio"] > 0.0
    assert result["forbidden_hits"] == []


def test_build_query_payload_includes_optional_query_profile():
    case = {
        "id": "GQ-19",
        "query": "sample",
        "collection_keys": ["fr"],
        "query_profile": "sample_pack",
    }

    payload, expected_route_keys, request_mode = eval_query_quality.build_query_payload(
        case,
        llm_provider="ollama",
        llm_model="llama3.1:8b",
        llm_base_url="http://localhost:11434",
        llm_api_key=None,
    )

    assert payload["query_profile"] == "sample_pack"
    assert expected_route_keys == ["fr"]
    assert request_mode == "explicit_single"


def test_evaluate_case_result_marks_fail_on_forbidden_hit_and_route_mismatch():
    case = {
        "id": "GQ-09",
        "bucket": "graph-candidate",
        "query": "sample",
        "collection_keys": ["uk", "ge", "fr"],
        "evaluation": {
            "min_answer_chars": 10,
            "must_include": ["뉴턴"],
            "must_not_include": ["환각"],
            "must_include_any": ["계몽주의"],
            "score_weights": {
                "precision": 0.4,
                "completeness": 0.4,
                "hallucination": 0.2,
            },
        },
    }
    body = {"answer": "뉴턴은 환각이라는 표현과 함께 서술된다."}
    headers = {"X-RAG-Collections": "rag_science_history_ge"}

    result = eval_query_quality.evaluate_case_result(
        case,
        status=200,
        body=body,
        headers=headers,
        latency_ms=50.0,
        expected_route_keys=["all"],
        request_mode="fallback_all_for_eval",
    )

    assert result["pass"] is False
    assert result["route_pass"] is False
    assert result["forbidden_hits"] == ["환각"]


def test_validate_fixture_collections_available_raises_for_empty_explicit_collection():
    fixtures = [
        {
            "id": "GQ-03",
            "query": "sample",
            "collection_keys": ["uk"],
        }
    ]
    payload = {
        "collections": [
            {"key": "all", "vectors": 37},
            {"key": "uk", "vectors": 0},
        ]
    }

    try:
        eval_query_quality.validate_fixture_collections_available(fixtures, payload)
    except ValueError as exc:
        assert "GQ-03: uk" in str(exc)
    else:
        raise AssertionError("expected ValueError for empty explicit collection")
