from __future__ import annotations

from api import routes_query


def _assert_query_error_shape(response, expected_status: int, expected_code: str):
    assert response.status_code == expected_status
    body = response.json()
    for key in ("code", "message", "request_id", "detail"):
        assert key in body
    assert body["code"] == expected_code
    assert body["detail"] == body["message"]
    assert response.headers.get("X-Request-ID") == body["request_id"]
    return body


def test_query_success_case(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda retriever, llm: object())
    monkeypatch.setattr(
        routes_query.query_service,
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
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: object())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 0)
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

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "bad-provider"})
    body = _assert_query_error_shape(response, 400, "INVALID_PROVIDER")
    assert "openai" in (body.get("hint") or "")


def test_query_llm_connection_failed(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )

    def _raise_connect_fail(**kwargs):
        raise RuntimeError("connect fail")

    monkeypatch.setattr(routes_query, "create_chat_llm", _raise_connect_fail)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama"})
    _assert_query_error_shape(response, 502, "LLM_CONNECTION_FAILED")


def test_query_timeout(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda retriever, llm: object())

    def _raise_timeout(chain, question, timeout_seconds=15):
        raise TimeoutError("timeout")

    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _raise_timeout)
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


def test_query_invalid_collection_limit(client):
    response = client.post(
        "/query",
        json={
            "query": "테스트",
            "llm_provider": "ollama",
            "collections": ["all", "fr", "ge"],
        },
    )
    body = _assert_query_error_shape(response, 400, "INVALID_COLLECTION")
    assert "최대" in (body.get("hint") or "")


def test_query_with_two_collections(client, monkeypatch):
    class DummyDB:
        def __init__(self, key: str):
            self.key = key

        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda key="all": DummyDB(key))
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda retriever, llm: object())
    monkeypatch.setattr(
        routes_query.query_service,
        "invoke_query_chain",
        lambda chain, question, timeout_seconds=15: "다중 컬렉션 응답",
    )

    response = client.post(
        "/query",
        json={
            "query": "테스트 질문",
            "llm_provider": "ollama",
            "collections": ["fr", "ge"],
        },
    )
    assert response.status_code == 200
    assert response.headers.get("X-RAG-Collection") == routes_query.collection_service.get_collection_name("fr")
    assert response.headers.get("X-RAG-Collections") == ",".join(
        [
            routes_query.collection_service.get_collection_name("fr"),
            routes_query.collection_service.get_collection_name("ge"),
        ]
    )
    assert response.json()["answer"] == "다중 컬렉션 응답"
