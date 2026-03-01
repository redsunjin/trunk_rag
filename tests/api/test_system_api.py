from __future__ import annotations

import app_api
from api import routes_system


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["collection_key"] == "all"
    assert "collection" in body
    assert "persist_dir" in body
    assert body["chunking_mode"] in {"char", "token"}


def test_collections_returns_200(client):
    response = client.get("/collections")
    assert response.status_code == 200
    body = response.json()
    assert body["default_collection_key"] == "all"
    assert isinstance(body["collections"], list)
    assert any(item["key"] == "all" for item in body["collections"])


def test_rag_docs_returns_200(client):
    response = client.get("/rag-docs")
    assert response.status_code == 200
    body = response.json()
    assert "docs" in body
    assert isinstance(body["docs"], list)


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
        lambda reset=True, collection_key="all": {
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
