from __future__ import annotations

import json

import app_api
from api import routes_system


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["collection_key"] == "all"
    assert body["default_runtime_collection_keys"] == ["all"]
    assert body["compatibility_bundle_key"] == "sample_pack"
    assert body["compatibility_bundle_optional"] is True
    assert body["seed_corpus_key"] == "sample_pack_bootstrap"
    assert body["seed_corpus_role"] == "demo_bootstrap"
    assert body["seed_corpus_dataset"] == "sample-eu-science-history"
    assert "not product-domain data" in body["seed_corpus_description"]
    assert "collection" in body
    assert "persist_dir" in body
    assert body["chunking_mode"] in {"char", "token"}
    assert isinstance(body["embedding_model"], str)
    assert isinstance(body["max_context_chars"], int)
    assert body["default_llm_provider"] in {"openai", "ollama", "lmstudio", "groq"}
    assert isinstance(body["default_llm_model"], str)
    assert body["runtime_profile_status"] in {"verified", "experimental", "not_recommended"}
    assert body["runtime_profile_scope"] in {"local", "cloud"}
    assert isinstance(body["runtime_profile_message"], str)
    assert isinstance(body["runtime_profile_recommendation"], str)
    assert isinstance(body["runtime_query_budget_profile"], str)
    assert isinstance(body["runtime_query_budget_summary"], str)
    assert body["embedding_fingerprint_status"] in {"ready", "missing", "mismatch", "empty"}
    assert body["compatibility_bundle_embedding_fingerprint_status"] in {"ready", "missing", "mismatch", "empty"}
    assert body["release_web_status"] in {
        "ready",
        "runtime_warning",
        "needs_verified_runtime",
        "needs_reindex",
    }
    assert isinstance(body["release_web_headline"], str)
    assert isinstance(body["release_web_steps"], list)
    assert any("run_doc_rag.bat" in step for step in body["release_web_steps"])


def test_collections_returns_200(client):
    response = client.get("/collections")
    assert response.status_code == 200
    body = response.json()
    assert body["default_collection_key"] == "all"
    assert isinstance(body["collections"], list)
    all_item = next(item for item in body["collections"] if item["key"] == "all")
    fr_item = next(item for item in body["collections"] if item["key"] == "fr")
    assert all_item["default_country"] == "all"
    assert all_item["default_doc_type"] == "summary"
    assert fr_item["default_country"] == "france"
    assert fr_item["default_doc_type"] == "country"


def test_ops_baseline_latest_returns_missing_when_report_does_not_exist(client, monkeypatch, tmp_path):
    missing_path = tmp_path / "ops_baseline_gate_latest.json"
    monkeypatch.setattr(routes_system, "OPS_BASELINE_REPORT_PATH", missing_path)

    response = client.get("/ops-baseline/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "missing"
    assert body["ready"] is False
    assert "scripts/check_ops_baseline_gate.py" in body["hint"]


def test_ops_baseline_latest_returns_report_summary(client, monkeypatch, tmp_path):
    report_path = tmp_path / "ops_baseline_gate_latest.json"
    report_path.write_text(
        json.dumps(
            {
                "generated_at": "2026-04-01T00:00:00Z",
                "ready": True,
                "runtime": {"ready": True},
                "collections": {"ready": True, "missing_keys": []},
                "diagnostics": [],
                "eval": {
                    "summary": {
                        "cases": 3,
                        "passed": 3,
                        "pass_rate": 1.0,
                        "avg_latency_ms": 1000.0,
                        "p95_latency_ms": 1500.0,
                        "avg_weighted_score": 0.96,
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(routes_system, "OPS_BASELINE_REPORT_PATH", report_path)

    response = client.get("/ops-baseline/latest")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["ready"] is True
    assert body["generated_at"] == "2026-04-01T00:00:00Z"
    assert body["summary"]["pass_rate"] == 1.0
    assert body["collections_ready"] is True
    assert body["runtime_ready"] is True


def test_rag_docs_returns_200(client):
    response = client.get("/rag-docs")
    assert response.status_code == 200
    body = response.json()
    assert "docs" in body
    assert isinstance(body["docs"], list)


def test_brand_assets_are_served(client):
    response = client.get("/assets/trunk-rag-mark.svg")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("image/svg+xml")
    assert "Trunk RAG mark" in response.text

    unsupported = client.get("/assets/not-an-image.txt")
    assert unsupported.status_code == 404


def test_rag_doc_success_and_404(client):
    docs = app_api.list_target_docs()
    assert docs, "테스트용 문서가 최소 1개 이상 필요합니다."

    target_name = docs[0]["name"]
    success = client.get(f"/rag-docs/{target_name}")
    assert success.status_code == 200
    success_body = success.json()
    assert success_body["name"] == target_name
    assert isinstance(success_body["content"], str)
    assert len(success_body["content"]) > 0

    missing = client.get("/rag-docs/not_exists.md")
    assert missing.status_code == 404


def test_build_validation_summary_includes_summary_text():
    summary = app_api.build_validation_summary(
        total_docs=5,
        usable_docs=3,
        rejected_items=[
            {"source": "a.md", "reasons": ["too_short"]},
            {"source": "b.md", "reasons": ["missing_header"]},
        ],
        warning_docs=1,
    )
    assert summary["total_docs"] == 5
    assert summary["usable_docs"] == 3
    assert summary["rejected_docs"] == 2
    assert summary["warning_docs"] == 1
    assert summary["usable_ratio"] == 0.6
    assert "usable=3" in summary["summary_text"]
    assert "usable_ratio=60.00%" in summary["summary_text"]


def test_reindex_returns_200_with_monkeypatch(client, monkeypatch):
    monkeypatch.setattr(
        routes_system.index_service,
        "reindex",
        lambda reset=True, collection_key="all", include_compatibility_bundle=False: {
            "docs": 5,
            "chunks": 37,
            "vectors": 37,
            "persist_dir": "mock",
            "collection": "mock_collection",
        },
    )
    response = client.post("/reindex", json={"reset": True})
    assert response.status_code == 200
    body = response.json()
    assert body["vectors"] == 37
