from __future__ import annotations

from chromadb.errors import InvalidDimensionException

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
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
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
    assert response.headers.get("X-RAG-Budget-Profile") == "not_recommended_local"
    assert response.headers.get("X-RAG-Route-Reason") == "default"
    assert response.headers.get("X-RAG-Query-Profile") == "generic"
    assert response.headers.get("X-RAG-Quality-Mode") == "balanced"
    assert response.headers.get("X-RAG-Quality-Stage") == "balanced"
    assert response.json() == {
        "answer": "모킹 응답",
        "provider": "ollama",
        "model": "qwen3:4b",
        "meta": None,
    }


def test_query_debug_response_includes_meta(client, monkeypatch):
    class DummyRetriever:
        def invoke(self, question):
            from langchain_core.documents import Document

            return [
                Document(
                    page_content="테스트 문서 본문",
                    metadata={"source": "fr_doc.md", "h2": "프랑스"},
                )
            ]

    class DummyDB:
        def __init__(self, key: str):
            self.key = key

        def as_retriever(self, **kwargs):
            return DummyRetriever()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda key="all": DummyDB(key))
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())

    def _build_query_chain(context_builder, llm):
        return context_builder

    def _invoke_query_chain(chain, question, timeout_seconds=15, trace=None):
        chain(question)
        if trace is not None:
            trace["invoke_ms"] = 123.4
            trace["status"] = "ok"
        return "메타 포함 응답"

    monkeypatch.setattr(routes_query.query_service, "build_query_chain", _build_query_chain)
    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _invoke_query_chain)

    response = client.post(
        "/query",
        json={"query": "프랑스와 독일 비교", "llm_provider": "ollama", "collections": ["fr", "ge"], "debug": True},
        headers={"X-Request-ID": "req-debug-1"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "메타 포함 응답"
    assert body["meta"]["request_id"] == "req-debug-1"
    assert body["meta"]["query_profile"] == "generic"
    assert body["meta"]["collections"] == ["fr", "ge"]
    assert body["meta"]["route_reason"] == "explicit_multi"
    assert body["meta"]["budget_profile"] == "not_recommended_local"
    assert body["meta"]["quality_mode"] == "balanced"
    assert body["meta"]["quality_stage"] == "balanced"
    assert body["meta"]["support_level"] == "limited"
    assert body["meta"]["support_reason"] == "single_or_short_context"
    assert body["meta"]["citations"] == ["fr_doc.md > 프랑스"]
    assert body["meta"]["invoke"]["status"] == "ok"
    assert body["meta"]["sources"]
    assert body["meta"]["sources"][0]["collection_key"] in {"fr", "ge"}


def test_query_quality_mode_appends_graph_lite_context(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    captured: dict[str, object] = {}
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3.5:9b-nvfp4", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(
        routes_query.query_service,
        "build_collection_context",
        lambda question, collection_keys, trace=None, budget=None: "base vector context",
    )
    monkeypatch.setattr(routes_query.graph_lite_service, "load_default_relation_snapshot", lambda: object())

    def _query_relation_snapshot(snapshot, question, *, collection_keys=None, max_hops=2, limit=8, force=False):
        captured["graph_collection_keys"] = collection_keys
        return {
            "mode": "graph_lite",
            "status": "hit",
            "fallback_used": False,
            "fallback_reason": None,
            "query_entities": ["newton", "voltaire"],
            "matched_entities": ["newton", "voltaire"],
            "relations": [
                {
                    "source": "newton",
                    "source_label": "Newton",
                    "target": "voltaire",
                    "target_label": "Voltaire",
                    "predicate": "influenced",
                    "weight": 3,
                    "score": 9.35,
                    "collections": ["uk", "fr"],
                    "evidence": [
                        {
                            "source": "uk.md",
                            "heading": "2. Newton",
                            "excerpt": "뉴턴의 국장은 볼테르에게 강한 인상을 주었다.",
                        }
                    ],
                }
            ],
            "latency_ms": 1.234,
        }

    monkeypatch.setattr(routes_query.graph_lite_service, "query_relation_snapshot", _query_relation_snapshot)

    def _build_query_chain(context_builder, llm, query_profile=None):
        return context_builder

    def _invoke_query_chain(chain, question, timeout_seconds=15, trace=None, query_profile=None):
        captured["context"] = chain(question)
        if trace is not None:
            trace["invoke_ms"] = 12.3
            trace["status"] = "ok"
        return "graph-lite quality 응답"

    monkeypatch.setattr(routes_query.query_service, "build_query_chain", _build_query_chain)
    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _invoke_query_chain)

    response = client.post(
        "/query",
        json={
            "query": "뉴턴과 볼테르의 관계가 계몽주의 확산으로 어떻게 이어졌는지 설명해줘.",
            "llm_provider": "ollama",
            "collections": ["uk", "fr"],
            "quality_mode": "quality",
            "quality_stage": "quality",
            "debug": True,
        },
        headers={"X-Request-ID": "req-graph-lite-hit"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-RAG-Graph-Lite") == "hit"
    assert captured["graph_collection_keys"] == ["uk", "fr"]
    assert "base vector context" in str(captured["context"])
    assert "[Graph-Lite Relations]" in str(captured["context"])
    body = response.json()
    assert body["answer"] == "graph-lite quality 응답"
    graph_meta = body["meta"]["context"]["graph_lite"]
    assert graph_meta["enabled"] is True
    assert graph_meta["status"] == "hit"
    assert graph_meta["relation_count"] == 1
    assert graph_meta["context_added"] is True


def test_query_quality_mode_falls_back_when_graph_lite_snapshot_missing(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    captured: dict[str, object] = {}
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3.5:9b-nvfp4", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(
        routes_query.query_service,
        "build_collection_context",
        lambda question, collection_keys, trace=None, budget=None: "base vector context",
    )
    monkeypatch.setattr(
        routes_query.graph_lite_service,
        "load_default_relation_snapshot",
        lambda: (_ for _ in ()).throw(FileNotFoundError("missing snapshot")),
    )
    monkeypatch.setattr(
        routes_query.graph_lite_service,
        "query_relation_snapshot",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("snapshot load should fail first")),
    )

    def _build_query_chain(context_builder, llm, query_profile=None):
        return context_builder

    def _invoke_query_chain(chain, question, timeout_seconds=15, trace=None, query_profile=None):
        captured["context"] = chain(question)
        if trace is not None:
            trace["invoke_ms"] = 12.3
            trace["status"] = "ok"
        return "fallback quality 응답"

    monkeypatch.setattr(routes_query.query_service, "build_query_chain", _build_query_chain)
    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _invoke_query_chain)

    response = client.post(
        "/query",
        json={
            "query": "뉴턴과 볼테르의 관계를 설명해줘.",
            "llm_provider": "ollama",
            "quality_mode": "quality",
            "quality_stage": "quality",
            "debug": True,
        },
        headers={"X-Request-ID": "req-graph-lite-fallback"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-RAG-Graph-Lite") == "fallback"
    assert captured["context"] == "base vector context"
    graph_meta = response.json()["meta"]["context"]["graph_lite"]
    assert graph_meta["enabled"] is True
    assert graph_meta["status"] == "fallback"
    assert graph_meta["fallback_reason"] == "snapshot_unavailable"
    assert graph_meta["context_added"] is False


def test_query_balanced_mode_does_not_load_graph_lite(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    captured: dict[str, object] = {}
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "gemma4:e2b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(
        routes_query.query_service,
        "build_collection_context",
        lambda question, collection_keys, trace=None, budget=None: "base vector context",
    )
    monkeypatch.setattr(
        routes_query.graph_lite_service,
        "load_default_relation_snapshot",
        lambda: (_ for _ in ()).throw(AssertionError("balanced mode must not load graph-lite")),
    )

    def _build_query_chain(context_builder, llm, query_profile=None):
        return context_builder

    def _invoke_query_chain(chain, question, timeout_seconds=15, trace=None, query_profile=None):
        captured["context"] = chain(question)
        if trace is not None:
            trace["invoke_ms"] = 12.3
            trace["status"] = "ok"
        return "balanced 응답"

    monkeypatch.setattr(routes_query.query_service, "build_query_chain", _build_query_chain)
    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _invoke_query_chain)

    response = client.post(
        "/query",
        json={"query": "뉴턴과 볼테르의 관계를 설명해줘.", "llm_provider": "ollama", "debug": True},
        headers={"X-Request-ID": "req-graph-lite-disabled"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-RAG-Graph-Lite") == "disabled"
    assert captured["context"] == "base vector context"
    graph_meta = response.json()["meta"]["context"]["graph_lite"]
    assert graph_meta["enabled"] is False
    assert graph_meta["status"] == "disabled"


def test_semantic_search_success_case(client, monkeypatch):
    from langchain_core.documents import Document

    class DummyRetriever:
        def __init__(self, key: str):
            self.key = key

        def invoke(self, question):
            if self.key == "ge":
                return [
                    Document(
                        page_content="독일 연구 대학과 실험실 문화에 대한 문서 본문입니다.",
                        metadata={"source": "ge_doc.md", "h2": "독일"},
                    )
                ]
            return [
                Document(
                    page_content="프랑스 과학 교육 제도와 학술 기관에 대한 문서 본문입니다.",
                    metadata={"source": "fr_doc.md", "h2": "프랑스"},
                )
            ]

    class DummyDB:
        def __init__(self, key: str):
            self.key = key

        def as_retriever(self, **kwargs):
            return DummyRetriever(self.key)

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda key="all": DummyDB(key))
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(routes_query.index_service, "get_collection_documents_from_store", lambda key="all": [])
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "create_chat_llm",
        lambda **kwargs: (_ for _ in ()).throw(AssertionError("semantic search must not call LLM")),
    )

    response = client.post(
        "/semantic-search",
        json={"query": "프랑스와 독일 비교", "collections": ["fr", "ge"], "max_results": 2},
        headers={"X-Request-ID": "req-semantic-1"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-semantic-1"
    assert response.headers.get("X-RAG-Search-Mode") == "semantic_fallback"
    assert response.headers.get("X-RAG-Route-Reason") == "explicit_multi"
    assert response.headers.get("X-RAG-Quality-Mode") == "semantic"
    body = response.json()
    assert body["query"] == "프랑스와 독일 비교"
    assert len(body["results"]) == 2
    assert body["results"][0]["source"] == "fr_doc.md"
    assert body["results"][0]["collection_key"] == "fr"
    assert body["meta"]["search_mode"] == "semantic_fallback"
    assert body["meta"]["collections"] == ["fr", "ge"]
    assert "mmr" in body["meta"]["retrieval_strategy"]


def test_semantic_search_vectorstore_empty(client, monkeypatch):
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 0)
    response = client.post(
        "/semantic-search",
        json={"query": "테스트"},
        headers={"X-Request-ID": "req-semantic-empty"},
    )
    body = _assert_query_error_shape(response, 400, "VECTORSTORE_EMPTY")
    assert body["request_id"] == "req-semantic-empty"
    assert "Reindex" in (body.get("hint") or "")


def test_query_supports_query_profile_override(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    captured: dict[str, object] = {}
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())

    def _build_query_chain(context_builder, llm, query_profile=None):
        captured["query_profile_from_build"] = query_profile
        return object()

    def _invoke_query_chain(chain, question, timeout_seconds=15, trace=None, query_profile=None):
        captured["query_profile_from_invoke"] = query_profile
        return "profile override 응답"

    monkeypatch.setattr(routes_query.query_service, "build_query_chain", _build_query_chain)
    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _invoke_query_chain)

    response = client.post(
        "/query",
        json={"query": "테스트 질문", "llm_provider": "ollama", "query_profile": "sample_pack"},
    )

    assert response.status_code == 200
    assert response.json()["answer"] == "profile override 응답"
    assert response.headers.get("X-RAG-Query-Profile") == "sample_pack"
    assert captured["query_profile_from_build"] == "sample_pack"
    assert captured["query_profile_from_invoke"] == "sample_pack"


def test_query_defaults_to_generic_all_route_even_when_env_prefers_sample_pack(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    captured: dict[str, object] = {}
    monkeypatch.setenv("DOC_RAG_QUERY_PROFILE", "sample_pack")
    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())

    def _build_query_chain(context_builder, llm, query_profile=None):
        captured["query_profile_from_build"] = query_profile
        return object()

    def _invoke_query_chain(chain, question, timeout_seconds=15, trace=None, query_profile=None):
        captured["query_profile_from_invoke"] = query_profile
        return "generic default 응답"

    monkeypatch.setattr(routes_query.query_service, "build_query_chain", _build_query_chain)
    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _invoke_query_chain)

    response = client.post(
        "/query",
        json={
            "query": "프랑스와 독일의 공통 과학적 성과를 비교해줘",
            "llm_provider": "ollama",
        },
    )

    assert response.status_code == 200
    assert response.headers.get("X-RAG-Collection") == routes_query.collection_service.get_collection_name("all")
    assert response.headers.get("X-RAG-Collections") == routes_query.collection_service.get_collection_name("all")
    assert response.headers.get("X-RAG-Route-Reason") == "default"
    assert response.headers.get("X-RAG-Query-Profile") == "generic"
    assert response.json()["answer"] == "generic default 응답"
    assert captured["query_profile_from_build"] == "generic"
    assert captured["query_profile_from_invoke"] == "generic"


def test_query_vectorstore_empty(client, monkeypatch):
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 0)
    response = client.post(
        "/query",
        json={"query": "테스트", "llm_provider": "ollama"},
        headers={"X-Request-ID": "req-empty-1"},
    )
    body = _assert_query_error_shape(response, 400, "VECTORSTORE_EMPTY")
    assert body["request_id"] == "req-empty-1"
    assert "run_doc_rag.bat" in (body.get("hint") or "")


def test_query_invalid_provider(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "bad-provider"})
    body = _assert_query_error_shape(response, 400, "INVALID_PROVIDER")
    assert "groq" in (body.get("hint") or "")


def test_query_llm_connection_failed(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )

    def _raise_connect_fail(**kwargs):
        raise RuntimeError("connect fail")

    monkeypatch.setattr(routes_query, "create_chat_llm", _raise_connect_fail)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama"})
    body = _assert_query_error_shape(response, 502, "LLM_CONNECTION_FAILED")
    assert "/intro" in (body.get("hint") or "")


def test_query_timeout(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://localhost:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda retriever, llm: object())
    captured: dict[str, object] = {}

    def _raise_timeout(chain, question, timeout_seconds=15):
        captured["timeout_seconds"] = timeout_seconds
        raise TimeoutError("timeout")

    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _raise_timeout)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama", "timeout_seconds": 60})
    body = _assert_query_error_shape(response, 504, "LLM_TIMEOUT")
    assert "/intro" in (body.get("hint") or "")
    assert captured["timeout_seconds"] == 60


def test_query_reports_embedding_dimension_mismatch(client, monkeypatch):
    class DummyDB:
        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda *args, **kwargs: DummyDB())
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
    monkeypatch.setattr(
        routes_query,
        "resolve_llm_config",
        lambda **kwargs: ("ollama", "qwen3:4b", None, "http://127.0.0.1:11434"),
    )
    monkeypatch.setattr(routes_query, "create_chat_llm", lambda **kwargs: object())
    monkeypatch.setattr(routes_query.query_service, "build_query_chain", lambda retriever, llm: object())

    def _raise_dimension_mismatch(chain, question, timeout_seconds=15):
        raise InvalidDimensionException("Embedding dimension 1024 does not match collection dimensionality 128")

    monkeypatch.setattr(routes_query.query_service, "invoke_query_chain", _raise_dimension_mismatch)
    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama"})
    body = _assert_query_error_shape(response, 409, "VECTORSTORE_EMBEDDING_MISMATCH")
    assert "Reindex" in (body.get("hint") or "")


def test_query_invalid_request_422(client):
    response = client.post("/query", json={"query": ""})
    body = _assert_query_error_shape(response, 422, "INVALID_REQUEST")
    assert "query" in (body.get("hint") or "")


def test_query_rejects_semantic_quality_mode(client):
    response = client.post(
        "/query",
        json={"query": "테스트", "quality_mode": "semantic"},
        headers={"X-Request-ID": "req-semantic-mode"},
    )
    body = _assert_query_error_shape(response, 400, "QUALITY_MODE_REQUIRES_SEMANTIC_SEARCH")
    assert body["request_id"] == "req-semantic-mode"
    assert "/semantic-search" in (body.get("hint") or "")


def test_query_feedback_accepts_local_record(client, monkeypatch):
    captured: dict[str, object] = {}

    def _append_feedback(payload):
        captured["payload"] = payload
        return {"id": "feedback-1", "storage": "chroma_db/query_feedback.jsonl", "record": payload}

    monkeypatch.setattr(routes_query.feedback_service, "append_feedback", _append_feedback)

    response = client.post(
        "/query-feedback",
        json={
            "request_id": "req-answer-1",
            "query": "테스트 질문",
            "answer": "테스트 답변",
            "rating": "negative",
            "reason_tags": ["needs_better_answer"],
            "quality_mode": "balanced",
            "quality_stage": "fast",
            "provider": "ollama",
            "model": "gemma4:e2b",
            "collections": ["all"],
        },
        headers={"X-Request-ID": "req-feedback-1"},
    )

    assert response.status_code == 200
    assert response.headers.get("X-Request-ID") == "req-feedback-1"
    assert response.headers.get("X-RAG-Feedback") == "accepted"
    assert response.json() == {
        "accepted": True,
        "feedback_id": "feedback-1",
        "request_id": "req-feedback-1",
        "storage": "chroma_db/query_feedback.jsonl",
    }
    assert captured["payload"]["rating"] == "negative"
    assert captured["payload"]["quality_stage"] == "fast"


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
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
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
    assert response.headers.get("X-RAG-Budget-Profile") == "not_recommended_local"
    assert response.headers.get("X-RAG-Route-Reason") == "explicit_multi"
    assert response.json()["answer"] == "다중 컬렉션 응답"


def test_query_auto_routes_multi_country_keywords_only_for_sample_pack_profile(client, monkeypatch):
    class DummyDB:
        def __init__(self, key: str):
            self.key = key

        def as_retriever(self, **kwargs):
            return object()

    monkeypatch.setattr(routes_query.index_service, "get_db", lambda key="all": DummyDB(key))
    monkeypatch.setattr(routes_query.index_service, "get_vector_count", lambda _db: 1)
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "ready", "message": "ok"},
    )
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
        lambda chain, question, timeout_seconds=15: "자동 다중 라우팅 응답",
    )

    response = client.post(
        "/query",
        json={
            "query": "프랑스와 독일의 공통 과학적 성과를 비교해줘",
            "llm_provider": "ollama",
            "query_profile": "sample_pack",
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
    assert response.headers.get("X-RAG-Budget-Profile") == "not_recommended_local"
    assert response.headers.get("X-RAG-Route-Reason") == "compatibility_keyword_multi"
    assert response.headers.get("X-RAG-Query-Profile") == "sample_pack"
    assert response.json()["answer"] == "자동 다중 라우팅 응답"


def test_query_blocks_embedding_fingerprint_mismatch(client, monkeypatch):
    monkeypatch.setattr(routes_query.index_service, "get_vector_count_snapshot", lambda key="all": 1)
    monkeypatch.setattr(
        routes_query.index_service,
        "get_embedding_fingerprint_status",
        lambda keys=None: {"status": "mismatch", "message": "fingerprint mismatch"},
    )

    response = client.post("/query", json={"query": "테스트", "llm_provider": "ollama"})

    body = _assert_query_error_shape(response, 409, "VECTORSTORE_EMBEDDING_MISMATCH")
    assert "DOC_RAG_EMBEDDING_MODEL" in (body.get("hint") or "")
