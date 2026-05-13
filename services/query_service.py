from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError
from typing import Callable

from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda, RunnablePassthrough

from core.settings import DEFAULT_QUERY_TIMEOUT_SECONDS, SEARCH_FETCH_K, SEARCH_K, SEARCH_LAMBDA
from services import index_service, runtime_service

PROMPT = ChatPromptTemplate.from_template(
    """당신은 유럽 과학사 질의응답 어시스턴트입니다.
반드시 [Context]에 있는 정보만 사용해 한국어로 답변하세요.
근거가 부족하면 '제공된 문서에서 확인되지 않습니다.'라고 답변하세요.

[Context]
{context}

[Question]
{question}

[Answer]
1) 핵심 답변:
2) 근거:
"""
)
INSUFFICIENT_ANSWER_MARKER = "제공된 문서에서 확인되지 않습니다."


def format_docs(docs: list[Document]) -> str:
    lines = []
    for idx, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        h2 = doc.metadata.get("h2", "")
        lines.append(f"[{idx}] source={source} h2={h2}\n{doc.page_content}")
    return "\n\n".join(lines)


def build_citation_sources(docs: list[Document], max_items: int = 5) -> list[dict[str, object]]:
    sources: list[dict[str, object]] = []
    for idx, doc in enumerate(docs[:max_items], 1):
        excerpt = doc.page_content.strip().replace("\n", " ")
        if len(excerpt) > 180:
            excerpt = excerpt[:180] + "..."
        sources.append(
            {
                "rank": idx,
                "source": str(doc.metadata.get("source", "unknown")),
                "source_file": str(doc.metadata.get("source_file", "")) or None,
                "h2": str(doc.metadata.get("h2", "")) or None,
                "country": str(doc.metadata.get("country", "")) or None,
                "doc_type": str(doc.metadata.get("doc_type", "")) or None,
                "topic": str(doc.metadata.get("topic", "")) or None,
                "year_text": str(doc.metadata.get("year_text", "")) or None,
                "scientist": str(doc.metadata.get("scientist", "")) or None,
                "excerpt": excerpt or None,
            }
        )
    return sources


def is_insufficient_answer(answer: str) -> bool:
    return INSUFFICIENT_ANSWER_MARKER in answer


def build_collection_context(
    question: str,
    collection_keys: list[str],
    on_docs: Callable[[list[Document]], None] | None = None,
) -> str:
    docs: list[Document] = []
    fingerprints: set[str] = set()

    for key in collection_keys:
        db = index_service.get_db(key)
        retriever = db.as_retriever(
            search_type="mmr",
            search_kwargs={
                "k": SEARCH_K,
                "fetch_k": SEARCH_FETCH_K,
                "lambda_mult": SEARCH_LAMBDA,
            },
        )
        for item in retriever.invoke(question):
            source = str(item.metadata.get("source", ""))
            h2 = str(item.metadata.get("h2", ""))
            fingerprint = f"{source}|{h2}|{item.page_content}"
            if fingerprint in fingerprints:
                continue
            fingerprints.add(fingerprint)
            docs.append(item)

    max_docs = max(SEARCH_K * len(collection_keys), SEARCH_K)
    selected_docs = docs[:max_docs]
    if on_docs is not None:
        on_docs(selected_docs)

    context = format_docs(selected_docs)
    max_context_chars = runtime_service.get_max_context_chars()
    if max_context_chars is not None and len(context) > max_context_chars:
        return context[:max_context_chars]
    return context


def build_query_chain(context_builder, llm):
    context_runnable = context_builder
    if callable(context_builder):
        context_runnable = RunnableLambda(context_builder)
    return (
        {"context": context_runnable, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )


def invoke_query_chain(
    chain,
    question: str,
    timeout_seconds: int = DEFAULT_QUERY_TIMEOUT_SECONDS,
) -> str:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(chain.invoke, question)
    try:
        return future.result(timeout=timeout_seconds)
    except FuturesTimeoutError as exc:
        future.cancel()
        raise TimeoutError("LLM invocation timed out.") from exc
    finally:
        executor.shutdown(wait=False, cancel_futures=True)
