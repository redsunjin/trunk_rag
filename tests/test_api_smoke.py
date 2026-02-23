from __future__ import annotations

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
    assert "collection" in body
    assert "persist_dir" in body


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
        lambda reset=True: {
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

    monkeypatch.setattr(app_api, "get_db", lambda: DummyDB())
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
    monkeypatch.setattr(app_api, "get_db", lambda: object())
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

    monkeypatch.setattr(app_api, "get_db", lambda: DummyDB())
    monkeypatch.setattr(app_api, "get_vector_count", lambda _db: 1)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "bad-provider"})
    body = _assert_query_error_shape(response, 400, "INVALID_PROVIDER")
    assert "openai" in (body.get("hint") or "")


def test_query_llm_connection_failed(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(app_api, "get_db", lambda: DummyDB())
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

    monkeypatch.setattr(app_api, "get_db", lambda: DummyDB())
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
