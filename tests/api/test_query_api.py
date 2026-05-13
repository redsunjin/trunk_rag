from __future__ import annotations

from langchain_core.documents import Document

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
        "sources": [],
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
    assert response.json()["sources"] == []


def test_query_response_includes_sources(client, monkeypatch):
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

    sample_docs = [
        Document(
            page_content="프랑스 과학사 본문 내용입니다.",
            metadata={
                "source": "fr.md",
                "h2": "## 프랑스",
                "country": "france",
                "doc_type": "country",
                "source_file": "fr_legacy.md",
                "topic": "science_timeline",
                "year_text": "18세기",
                "scientist": "라부아지에",
            },
        )
    ]

    def _mock_build_collection_context(question, collection_keys, on_docs=None):
        if on_docs is not None:
            on_docs(sample_docs)
        return "context"

    monkeypatch.setattr(routes_query.query_service, "build_collection_context", _mock_build_collection_context)
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda context_builder, llm: context_builder)
    monkeypatch.setattr(
        routes_query.query_service,
        "invoke_query_chain",
        lambda chain, question, timeout_seconds=15: (chain(question), "근거 기반 응답")[1],
    )

    response = client.post("/query", json={"query": "프랑스 과학사 요약", "llm_provider": "ollama"})
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "근거 기반 응답"
    assert len(body["sources"]) == 1
    assert body["sources"][0]["rank"] == 1
    assert body["sources"][0]["source"] == "fr.md"
    assert body["sources"][0]["source_file"] == "fr_legacy.md"
    assert body["sources"][0]["country"] == "france"
    assert body["sources"][0]["topic"] == "science_timeline"
    assert body["sources"][0]["year_text"] == "18세기"
    assert body["sources"][0]["scientist"] == "라부아지에"


def test_query_trace_writes_record_when_enabled(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    traces: list[dict[str, object]] = []

    monkeypatch.setattr(routes_query.runtime_service, "is_query_trace_enabled", lambda: True)
    monkeypatch.setattr(routes_query.query_trace_service, "append_query_trace", lambda record: traces.append(record))
    monkeypatch.setattr(
        routes_query.query_trace_service,
        "summarize_docs_for_trace",
        lambda docs: [{"rank": 1, "source": "trace.md", "h2": "h2"}],
    )
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())

    def _mock_build_collection_context(question, collection_keys, on_docs=None):
        if on_docs is not None:
            on_docs([])
        return "context"

    monkeypatch.setattr(routes_query.query_service, "build_collection_context", _mock_build_collection_context)
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda context_builder, llm: context_builder)
    monkeypatch.setattr(
        routes_query.query_service,
        "invoke_query_chain",
        lambda chain, question, timeout_seconds=15: (chain(question), "모킹 응답")[1],
    )

    response = client.post(
        "/query",
        json={"query": "추적 로그 테스트", "llm_provider": "ollama"},
        headers={"X-Request-ID": "req-trace-1"},
    )
    assert response.status_code == 200
    assert len(traces) == 1
    assert traces[0]["request_id"] == "req-trace-1"
    assert traces[0]["code"] == "OK"
    assert traces[0]["status_code"] == 200
    assert traces[0]["top_sources"] == [{"rank": 1, "source": "trace.md", "h2": "h2"}]


def test_query_trace_writes_error_record_when_enabled(client, monkeypatch):
    traces: list[dict[str, object]] = []
    monkeypatch.setattr(routes_query.runtime_service, "is_query_trace_enabled", lambda: True)
    monkeypatch.setattr(routes_query.query_trace_service, "append_query_trace", lambda record: traces.append(record))

    response = client.post(
        "/query",
        json={"query": "테스트", "llm_provider": "bad-provider"},
        headers={"X-Request-ID": "req-trace-error-1"},
    )
    assert response.status_code == 400
    assert len(traces) == 1
    assert traces[0]["request_id"] == "req-trace-error-1"
    assert traces[0]["code"] == "INVALID_PROVIDER"
    assert traces[0]["status_code"] == 400


def test_query_failure_note_writes_error_record_when_enabled(client, monkeypatch):
    notes: list[dict[str, object]] = []
    monkeypatch.setattr(routes_query.runtime_service, "is_query_failure_note_enabled", lambda: True)
    monkeypatch.setattr(
        routes_query.query_failure_note_service,
        "append_failure_note",
        lambda record: notes.append(record),
    )

    response = client.post(
        "/query",
        json={"query": "테스트", "llm_provider": "bad-provider"},
        headers={"X-Request-ID": "req-failure-note-1"},
    )
    assert response.status_code == 400
    assert len(notes) == 1
    note = notes[0]
    assert note["request_id"] == "req-failure-note-1"
    assert note["type"] == "error"
    assert note["code"] == "INVALID_PROVIDER"
    assert note["status_code"] == 400
    assert note["query"] == "테스트"
    assert "top_sources" in note


def test_query_failure_note_writes_insufficient_record_when_enabled(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    notes: list[dict[str, object]] = []
    monkeypatch.setattr(routes_query.runtime_service, "is_query_failure_note_enabled", lambda: True)
    monkeypatch.setattr(
        routes_query.query_failure_note_service,
        "append_failure_note",
        lambda record: notes.append(record),
    )
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())

    def _mock_build_collection_context(question, collection_keys, on_docs=None):
        if on_docs is not None:
            on_docs([])
        return "context"

    monkeypatch.setattr(routes_query.query_service, "build_collection_context", _mock_build_collection_context)
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda context_builder, llm: context_builder)
    monkeypatch.setattr(
        routes_query.query_service,
        "invoke_query_chain",
        lambda chain, question, timeout_seconds=15: (
            chain(question),
            "제공된 문서에서 확인되지 않습니다.",
        )[1],
    )

    response = client.post("/query", json={"query": "근거 없는 질문", "llm_provider": "ollama"})
    assert response.status_code == 200
    assert len(notes) == 1
    note = notes[0]
    assert note["type"] == "insufficient"
    assert note["code"] == "INSUFFICIENT_CONTEXT"
    assert note["status_code"] == 200
    assert note["answer"] == "제공된 문서에서 확인되지 않습니다."
