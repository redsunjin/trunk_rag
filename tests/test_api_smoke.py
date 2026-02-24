from __future__ import annotations

from pathlib import Path

import app_api


def _assert_query_error_shape(response, expected_status: int, expected_code: str):
    assert response.status_code == expected_status
    body = response.json()
    for key in ("code", "message", "request_id", "detail"):
        assert key in body
    assert body["code"] == expected_code
    assert body["detail"] == body["message"]
    assert response.headers.get("X-Request-ID") == body["request_id"]
    return body


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["collection_key"] == "all"
    assert "collection" in body
    assert "persist_dir" in body


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


def test_reindex_returns_200_with_monkeypatch(client, monkeypatch):
    monkeypatch.setattr(
        app_api,
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


def test_query_success_case(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(app_api, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(app_api, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        app_api,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(app_api, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(app_api, "build_query_chain", lambda retriever, llm: object())
    monkeypatch.setattr(
        app_api,
        "invoke_query_chain",
        lambda chain, question, timeout_seconds=15: "모킹 응답",
    )

    response = client.post(
        "/query",
        json={"query": "테스트 질문", "llm_provider": "ollama"},
        headers={"X-Request-ID": "req-success-1"},
    )
    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-success-1"
    assert response.json() == {
        "answer": "모킹 응답",
        "provider": "ollama",
        "model": "qwen3:4b",
    }


def test_query_vectorstore_empty(client, monkeypatch):
    monkeypatch.setattr(app_api, "get_db", lambda *args, **kwargs: object())
    monkeypatch.setattr(app_api, "get_vector_count", lambda _db: 0)
    response = client.post(
        "/query",
        json={"query": "테스트", "llm_provider": "ollama"},
        headers={"X-Request-ID": "req-empty-1"},
    )
    body = _assert_query_error_shape(response, 400, "VECTORSTORE_EMPTY")
    assert body["request_id"] == "req-empty-1"


def test_query_invalid_provider(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(app_api, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(app_api, "get_vector_count", lambda _db: 1)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "bad-provider"})
    body = _assert_query_error_shape(response, 400, "INVALID_PROVIDER")
    assert "openai" in (body.get("hint") or "")


def test_query_llm_connection_failed(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(app_api, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(app_api, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        app_api,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )

    def _raise_connect_fail(**kwargs):
        raise RuntimeError("connect fail")

    monkeypatch.setattr(app_api, "create_chat_llm", _raise_connect_fail)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama"})
    _assert_query_error_shape(response, 502, "LLM_CONNECTION_FAILED")


def test_query_timeout(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(app_api, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(app_api, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        app_api,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(app_api, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(app_api, "build_query_chain", lambda retriever, llm: object())

    def _raise_timeout(chain, question, timeout_seconds=15):
        raise TimeoutError("timeout")

    monkeypatch.setattr(app_api, "invoke_query_chain", _raise_timeout)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama"})
    _assert_query_error_shape(response, 504, "LLM_TIMEOUT")


def test_query_invalid_request_422(client):
    response = client.post("/query", json={"query": ""})
    body = _assert_query_error_shape(response, 422, "INVALID_REQUEST")
    assert "query" in (body.get("hint") or "")


def test_query_invalid_collection(client):
    response = client.post(
        "/query",
        json={"query": "테스트", "llm_provider": "ollama", "collection": "not-supported"},
    )
    body = _assert_query_error_shape(response, 400, "INVALID_COLLECTION")
    assert "지원값" in (body.get("hint") or "")


def test_admin_auth_success_and_failure(client, monkeypatch):
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "123456")

    success = client.post("/admin/auth", json={"code": "123456"})
    assert success.status_code == 200
    assert success.json() == {"ok": True}

    failure = client.post("/admin/auth", json={"code": "wrong"})
    assert failure.status_code == 401


def _sample_markdown() -> str:
    return "## 테스트 섹션\n이 문서는 업로드 요청 테스트를 위한 충분한 길이의 본문을 포함합니다."


def test_upload_request_create_pending_and_list(client, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app_api, "upload_request_store_path", lambda: tmp_path / "upload_requests.json")
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")

    create = client.post(
        "/upload-requests",
        json={
            "source_name": "sample_upload.md",
            "collection": "fr",
            "country": "france",
            "doc_type": "country",
            "content": _sample_markdown(),
        },
    )
    assert create.status_code == 200
    body = create.json()
    assert body["auto_approve"] is False
    assert body["request"]["status"] == "pending"
    request_id = body["request"]["id"]

    listing = client.get("/upload-requests", params={"status": "pending"})
    assert listing.status_code == 200
    listed = listing.json()
    assert listed["counts"]["pending"] == 1
    assert any(item["id"] == request_id for item in listed["requests"])


def test_upload_request_approve_and_reject(client, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(app_api, "upload_request_store_path", lambda: tmp_path / "upload_requests.json")
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "admin999")
    monkeypatch.setattr(
        app_api,
        "index_documents_for_collection",
        lambda docs, collection_key, reset: {
            "chunks_added": len(docs),
            "vectors": 99,
            "cap": {"soft_cap": 30000, "hard_cap": 50000},
            "collection": "mock_collection",
            "collection_key": collection_key,
        },
    )

    first = client.post(
        "/upload-requests",
        json={
            "source_name": "approve_target.md",
            "collection": "all",
            "content": _sample_markdown(),
        },
    )
    assert first.status_code == 200
    first_id = first.json()["request"]["id"]

    approved = client.post(f"/upload-requests/{first_id}/approve", json={"code": "admin999"})
    assert approved.status_code == 200
    assert approved.json()["request"]["status"] == "approved"

    second = client.post(
        "/upload-requests",
        json={
            "source_name": "reject_target.md",
            "collection": "all",
            "content": _sample_markdown(),
        },
    )
    assert second.status_code == 200
    second_id = second.json()["request"]["id"]

    rejected = client.post(
        f"/upload-requests/{second_id}/reject",
        json={"code": "admin999", "reason": "형식 미흡"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["request"]["status"] == "rejected"
    assert rejected.json()["request"]["rejected_reason"] == "형식 미흡"
