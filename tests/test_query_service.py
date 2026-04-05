from __future__ import annotations

import time

from langchain_core.documents import Document

from services import query_service


def test_postprocess_answer_strips_trailing_insufficient_note_when_answer_exists():
    answer = (
        "에콜 폴리테크니크는 프랑스 과학 인재 양성의 핵심 기관입니다.\n\n"
        "제공된 문서에서 확인되지 않습니다."
    )

    resolved = query_service.postprocess_answer(
        "에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘.",
        answer,
    )

    assert "제공된 문서에서 확인되지 않습니다." not in resolved
    assert resolved == "에콜 폴리테크니크는 프랑스 과학 인재 양성의 핵심 기관입니다."


def test_postprocess_answer_keeps_generic_answer_without_sample_pack_expansion():
    answer = "뉴턴의 국장은 영국 사회에서 과학이 왕권과 동등한 권위를 얻었음을 보여줬습니다."

    resolved = query_service.postprocess_answer(
        "뉴턴의 국장이 영국 사회에서 무엇을 상징했는지 설명해줘.",
        answer,
    )

    assert resolved == answer


def test_postprocess_answer_keeps_generic_comparison_answer_without_sample_pack_expansion():
    answer = (
        "프랑스의 에콜 폴리테크니크는 국가 주도의 실용 교육을 강화했습니다. "
        "독일의 훔볼트 대학은 연구와 학문 자유를 중심으로 엘리트 교육을 조직했습니다."
    )

    resolved = query_service.postprocess_answer(
        "프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학이 인재 양성에서 어떻게 다른지 비교해줘.",
        answer,
    )

    assert resolved == answer


def test_postprocess_answer_adds_sample_pack_symbolic_lead_when_profile_enabled(monkeypatch):
    monkeypatch.setenv(query_service.QUERY_PROFILE_ENV_KEY, query_service.QUERY_PROFILE_SAMPLE_PACK)
    answer = "뉴턴의 국장은 영국 사회에서 과학이 왕권과 동등한 권위를 얻었음을 보여줬습니다."

    resolved = query_service.postprocess_answer(
        "뉴턴의 국장이 영국 사회에서 무엇을 상징했는지 설명해줘.",
        answer,
    )

    assert "상징" in resolved
    assert "과학자" in resolved
    assert "영향력" in resolved
    assert "국왕" in resolved
    assert len(resolved) >= 120


def test_postprocess_answer_adds_sample_pack_comparison_lead_when_profile_enabled(monkeypatch):
    monkeypatch.setenv(query_service.QUERY_PROFILE_ENV_KEY, query_service.QUERY_PROFILE_SAMPLE_PACK)
    answer = (
        "프랑스의 에콜 폴리테크니크는 국가 주도의 실용 교육을 강화했습니다. "
        "독일의 훔볼트 대학은 연구와 학문 자유를 중심으로 엘리트 교육을 조직했습니다."
    )

    resolved = query_service.postprocess_answer(
        "프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학이 인재 양성에서 어떻게 다른지 비교해줘.",
        answer,
    )

    assert "비교" in resolved
    assert "에콜 폴리테크니크" in resolved
    assert "훔볼트 대학" in resolved
    assert "인재 양성" in resolved


def test_postprocess_answer_extracts_final_answer_block_only():
    answer = (
        "<final_answer>에콜 폴리테크니크는 프랑스 과학 인재 양성을 국가 중심 교육으로 조직했습니다."
        "</final_answer>\n\n"
        "Thinking Process:\n1. Analyze the Request"
    )

    resolved = query_service.postprocess_answer(
        "에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘.",
        answer,
    )

    assert "Thinking Process" not in resolved
    assert "Analyze the Request" not in resolved
    assert "<final_answer>" not in resolved
    assert "에콜 폴리테크니크" in resolved


def test_postprocess_answer_strips_reasoning_suffix_without_final_answer_block():
    answer = (
        "요약하면, 뉴턴의 국장은 영국 사회에서 과학자의 권위와 영향력이 커졌음을 상징했습니다.\n\n"
        "Thinking Process:\n\n"
        "1. **Analyze the Request:**\n"
        "* Constraint 1: Use only context."
    )

    resolved = query_service.postprocess_answer(
        "뉴턴의 국장이 영국 사회에서 무엇을 상징했는지 설명해줘.",
        answer,
    )

    assert "Thinking Process" not in resolved
    assert "Analyze the Request" not in resolved
    assert "Constraint 1" not in resolved
    assert "상징" in resolved


def test_postprocess_answer_returns_insufficient_when_only_reasoning_leaks():
    answer = "Thinking Process:\n1. **Analyze the Request:**\n* Constraint 1: Use only context."

    resolved = query_service.postprocess_answer(
        "에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘.",
        answer,
    )

    assert resolved == query_service.INSUFFICIENT_ANSWER_TEXT


def test_postprocess_answer_returns_insufficient_for_english_reasoning_intro():
    answer = "Here's a thinking process to construct the answer:"

    resolved = query_service.postprocess_answer(
        "문서 기준으로 뉴턴의 국장이 당시 영국에서 과학의 위상을 어떻게 보여줬는지 설명해줘.",
        answer,
    )

    assert resolved == query_service.INSUFFICIENT_ANSWER_TEXT


def test_get_prompt_template_defaults_to_generic_profile(monkeypatch):
    monkeypatch.delenv(query_service.QUERY_PROFILE_ENV_KEY, raising=False)

    prompt = query_service.get_prompt_template()
    messages = prompt.format_messages(context="문맥", question="질문")

    assert query_service.get_query_profile() == query_service.QUERY_PROFILE_GENERIC
    assert "로컬 RAG 질의응답 어시스턴트" in messages[0].content
    assert "유럽 과학사" not in messages[0].content
    assert "Here's a thinking process" in messages[0].content
    assert "태그 앞뒤에 설명" in messages[1].content


def test_get_prompt_template_supports_sample_pack_profile(monkeypatch):
    monkeypatch.setenv(query_service.QUERY_PROFILE_ENV_KEY, query_service.QUERY_PROFILE_SAMPLE_PACK)

    prompt = query_service.get_prompt_template()
    messages = prompt.format_messages(context="문맥", question="질문")

    assert query_service.get_query_profile() == query_service.QUERY_PROFILE_SAMPLE_PACK
    assert "유럽 과학사 질의응답 어시스턴트" in messages[0].content


def test_extract_lexical_query_terms_filters_wrapper_terms_and_particles():
    terms = query_service.extract_lexical_query_terms(
        "문서 기준으로 에콜 폴리테크니크가 어떤 방식으로 과학 인재를 길렀는지 요약해줘."
    )

    assert "문서" not in terms
    assert "기준" not in terms
    assert "요약해줘" not in terms
    assert "에콜" in terms
    assert "폴리테크니크" in terms
    assert "방식" in terms
    assert "인재" in terms


def test_rerank_docs_with_light_lexical_boost_prioritizes_matching_doc():
    docs = [
        Document(page_content="일반 소개 문단", metadata={"source": "all.md", "h2": "개요"}),
        Document(
            page_content="에콜 폴리테크니크는 프랑스에서 과학 인재를 길러낸 핵심 기관이다.",
            metadata={"source": "fr.md", "h2": "에콜 폴리테크니크"},
        ),
    ]

    reranked, info = query_service.rerank_docs_with_light_lexical_boost(
        docs,
        "문서 기준으로 에콜 폴리테크니크가 어떤 방식으로 과학 인재를 길렀는지 요약해줘.",
    )

    assert reranked[0].metadata["source"] == "fr.md"
    assert info["applied"] is True
    assert info["strategy"] == query_service.RETRIEVAL_STRATEGY_MMR_WITH_LEXICAL
    assert "에콜" in info["query_terms"]


def test_merge_docs_with_light_hybrid_candidates_adds_matching_doc_from_collection_pool():
    dense_docs = [
        Document(page_content="일반 소개 문단", metadata={"source": "all.md", "h2": "개요"}),
    ]
    collection_docs = [
        Document(page_content="일반 소개 문단", metadata={"source": "all.md", "h2": "개요"}),
        Document(
            page_content="에콜 폴리테크니크는 프랑스 과학 인재 양성 기관이다.",
            metadata={"source": "fr.md", "h2": "기관"},
        ),
    ]

    merged, info = query_service.merge_docs_with_light_hybrid_candidates(
        dense_docs,
        collection_docs,
        "에콜 폴리테크니크 과학 인재",
    )

    assert len(merged) == 2
    assert merged[1].metadata["source"] == "fr.md"
    assert info["applied"] is True
    assert info["candidate_count"] == 1
    assert info["candidate_limit"] == query_service.HYBRID_LEXICAL_CANDIDATE_LIMIT
    assert info["collection_doc_count"] == 2
    assert info["scan_doc_count"] == 2
    assert info["matched_doc_count"] == 1


def test_merge_docs_with_light_hybrid_candidates_skips_large_collection(monkeypatch):
    monkeypatch.setattr(query_service, "HYBRID_LEXICAL_SCAN_MAX_DOCS", 1)
    dense_docs = [
        Document(page_content="일반 소개 문단", metadata={"source": "all.md", "h2": "개요"}),
    ]
    collection_docs = [
        Document(page_content="일반 소개 문단", metadata={"source": "all.md", "h2": "개요"}),
        Document(
            page_content="에콜 폴리테크니크는 프랑스 과학 인재 양성 기관이다.",
            metadata={"source": "fr.md", "h2": "기관"},
        ),
    ]

    merged, info = query_service.merge_docs_with_light_hybrid_candidates(
        dense_docs,
        collection_docs,
        "에콜 폴리테크니크 과학 인재",
    )

    assert merged == dense_docs
    assert info["applied"] is False
    assert info["candidate_count"] == 0
    assert info["collection_doc_count"] == 2
    assert info["scan_doc_count"] == 0
    assert info["matched_doc_count"] == 0
    assert info["skipped"] == "collection_too_large"


def test_build_collection_context_populates_trace(monkeypatch):
    class DummyRetriever:
        def invoke(self, question):
            assert question == "테스트 질문"
            return [
                Document(page_content="A", metadata={"source": "fr.md", "h2": "역할"}),
                Document(page_content="A", metadata={"source": "fr.md", "h2": "역할"}),
                Document(page_content="B", metadata={"source": "fr.md", "h2": "교육"}),
            ]

    class DummyDB:
        def as_retriever(self, **kwargs):
            return DummyRetriever()

    monkeypatch.setattr(query_service.index_service, "get_db", lambda key: DummyDB())
    monkeypatch.setattr(query_service.index_service, "get_collection_documents_from_store", lambda key: [])
    monkeypatch.setattr(query_service.runtime_service, "get_max_context_chars", lambda: 100)

    trace: dict[str, object] = {}
    context = query_service.build_collection_context("테스트 질문", ["fr"], trace=trace)

    assert context
    assert trace["collections"] == ["fr"]
    assert trace["docs_total"] == 2
    assert trace["max_docs"] >= 1
    assert trace["context_chars"] == len(context)
    assert trace["retrieval_strategy"] == query_service.RETRIEVAL_STRATEGY_MMR
    assert trace["lexical_boost_applied"] is False
    assert trace["hybrid_candidate_merge_applied"] is False
    assert trace["hybrid_candidate_count"] == 0
    assert trace["hybrid_candidate_limit"] == min(query_service.HYBRID_LEXICAL_CANDIDATE_LIMIT, trace["per_collection_k"])
    assert trace["hybrid_scan_limit"] == query_service.HYBRID_LEXICAL_SCAN_MAX_DOCS
    assert trace["hybrid_scan_doc_count"] == 0
    assert trace["hybrid_skipped_collections"] == [{"key": "fr", "reason": "empty_collection"}]
    assert trace["lexical_query_terms"] == ["테스트", "질문"]
    assert trace["elapsed_ms"] >= 0
    assert trace["collection_stats"] == [
        {
            "key": "fr",
            "retrieved_docs": 3,
            "unique_docs": 2,
            "collection_doc_count": 0,
            "hybrid_scan_doc_count": 0,
            "hybrid_matched_doc_count": 0,
            "hybrid_candidate_count": 0,
            "hybrid_candidate_limit": min(query_service.HYBRID_LEXICAL_CANDIDATE_LIMIT, trace["per_collection_k"]),
            "hybrid_skipped": "empty_collection",
            "elapsed_ms": trace["collection_stats"][0]["elapsed_ms"],
        }
    ]


def test_build_collection_context_applies_light_lexical_boost(monkeypatch):
    class DummyRetriever:
        def invoke(self, question):
            assert question == "에콜 폴리테크니크 과학 인재"
            return [
                Document(page_content="일반 개요", metadata={"source": "all.md", "h2": "개요"}),
                Document(
                    page_content="에콜 폴리테크니크는 프랑스 과학 인재 양성 기관이다.",
                    metadata={"source": "fr.md", "h2": "기관"},
                ),
            ]

    class DummyDB:
        def as_retriever(self, **kwargs):
            return DummyRetriever()

    monkeypatch.setattr(query_service.index_service, "get_db", lambda key: DummyDB())
    monkeypatch.setattr(query_service.index_service, "get_collection_documents_from_store", lambda key: [])
    monkeypatch.setattr(query_service.runtime_service, "get_max_context_chars", lambda: 200)

    trace: dict[str, object] = {}
    context = query_service.build_collection_context("에콜 폴리테크니크 과학 인재", ["fr"], trace=trace)

    assert context.startswith("[1] source=fr.md")
    assert trace["retrieval_strategy"] == query_service.RETRIEVAL_STRATEGY_MMR_WITH_LEXICAL
    assert trace["lexical_boost_applied"] is True
    assert trace["hybrid_candidate_merge_applied"] is False
    assert trace["hybrid_scan_doc_count"] == 0
    assert trace["hybrid_skipped_collections"] == [{"key": "fr", "reason": "empty_collection"}]
    assert "에콜" in trace["lexical_query_terms"]


def test_build_collection_context_applies_light_hybrid_candidate_merge(monkeypatch):
    class DummyRetriever:
        def invoke(self, question):
            assert question == "에콜 폴리테크니크 과학 인재"
            return [
                Document(page_content="일반 개요", metadata={"source": "all.md", "h2": "개요"}),
            ]

    class DummyDB:
        def as_retriever(self, **kwargs):
            return DummyRetriever()

    monkeypatch.setattr(query_service.index_service, "get_db", lambda key: DummyDB())
    monkeypatch.setattr(
        query_service.index_service,
        "get_collection_documents_from_store",
        lambda key: [
            Document(page_content="일반 개요", metadata={"source": "all.md", "h2": "개요"}),
            Document(
                page_content="에콜 폴리테크니크는 프랑스 과학 인재 양성 기관이다.",
                metadata={"source": "fr.md", "h2": "기관"},
            ),
        ],
    )
    monkeypatch.setattr(query_service.runtime_service, "get_max_context_chars", lambda: 200)

    trace: dict[str, object] = {}
    context = query_service.build_collection_context("에콜 폴리테크니크 과학 인재", ["fr"], trace=trace)

    assert context.startswith("[1] source=fr.md")
    assert trace["retrieval_strategy"] == query_service.RETRIEVAL_STRATEGY_MMR_WITH_HYBRID_AND_LEXICAL
    assert trace["hybrid_candidate_merge_applied"] is True
    assert trace["hybrid_candidate_count"] == 1
    assert trace["hybrid_scan_doc_count"] == 2
    assert trace["hybrid_skipped_collections"] == []
    assert trace["lexical_boost_applied"] is True


def test_build_collection_context_records_hybrid_scan_skip(monkeypatch):
    class DummyRetriever:
        def invoke(self, question):
            assert question == "테스트 질문"
            return [
                Document(page_content="A", metadata={"source": "fr.md", "h2": "역할"}),
            ]

    class DummyDB:
        def as_retriever(self, **kwargs):
            return DummyRetriever()

    monkeypatch.setattr(query_service, "HYBRID_LEXICAL_SCAN_MAX_DOCS", 1)
    monkeypatch.setattr(query_service.index_service, "get_db", lambda key: DummyDB())
    monkeypatch.setattr(
        query_service.index_service,
        "get_collection_documents_from_store",
        lambda key: [
            Document(page_content="A", metadata={"source": "fr.md", "h2": "역할"}),
            Document(page_content="B", metadata={"source": "fr.md", "h2": "교육"}),
        ],
    )
    monkeypatch.setattr(query_service.runtime_service, "get_max_context_chars", lambda: 100)

    trace: dict[str, object] = {}
    context = query_service.build_collection_context("테스트 질문", ["fr"], trace=trace)

    assert context
    assert trace["retrieval_strategy"] == query_service.RETRIEVAL_STRATEGY_MMR
    assert trace["hybrid_candidate_merge_applied"] is False
    assert trace["hybrid_candidate_count"] == 0
    assert trace["hybrid_scan_doc_count"] == 0
    assert trace["hybrid_skipped_collections"] == [{"key": "fr", "reason": "collection_too_large"}]
    assert trace["collection_stats"][0]["collection_doc_count"] == 2
    assert trace["collection_stats"][0]["hybrid_scan_doc_count"] == 0
    assert trace["collection_stats"][0]["hybrid_candidate_count"] == 0
    assert trace["collection_stats"][0]["hybrid_skipped"] == "collection_too_large"


def test_invoke_query_chain_populates_trace():
    class DummyChain:
        def invoke(self, question):
            assert question == "질문"
            return "짧은 답변"

    trace: dict[str, object] = {}
    answer = query_service.invoke_query_chain(DummyChain(), "질문", timeout_seconds=1, trace=trace)

    assert answer
    assert trace["status"] == "ok"
    assert trace["invoke_ms"] >= 0


def test_invoke_query_chain_populates_timeout_trace():
    class DummyChain:
        def invoke(self, question):
            time.sleep(0.05)
            return "늦은 답변"

    trace: dict[str, object] = {}

    try:
        query_service.invoke_query_chain(DummyChain(), "질문", timeout_seconds=0.01, trace=trace)
    except TimeoutError:
        pass
    else:
        raise AssertionError("TimeoutError was not raised")

    assert trace["status"] == "timeout"
    assert trace["invoke_ms"] >= 0
