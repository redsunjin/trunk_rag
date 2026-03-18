from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FuturesTimeoutError

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
질문에 들어 있는 핵심 표현(예: 역할, 비교, 상징, 인재 양성)은 답변 문장에 직접 반영하세요.
비교 질문이면 공통점과 차이점을 모두 적고, 각 대상을 최소 한 번씩 명시하세요.
답변은 너무 짧게 끝내지 말고 핵심 답변을 2~4문장으로 작성하세요.

[Context]
{context}

[Question]
{question}

[Answer]
1) 핵심 답변:
2) 근거:
"""
)


def format_docs(docs: list[Document]) -> str:
    lines = []
    for idx, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        h2 = doc.metadata.get("h2", "")
        lines.append(f"[{idx}] source={source} h2={h2}\n{doc.page_content}")
    return "\n\n".join(lines)


def format_docs_with_limit(docs: list[Document], *, max_chars: int | None) -> str:
    if max_chars is None:
        return format_docs(docs)

    lines: list[str] = []
    current_length = 0
    for idx, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        h2 = doc.metadata.get("h2", "")
        rendered = f"[{idx}] source={source} h2={h2}\n{doc.page_content}"
        separator = "\n\n" if lines else ""
        remaining = max_chars - current_length - len(separator)
        if remaining <= 0:
            break
        if len(rendered) > remaining:
            rendered = rendered[:remaining].rstrip()
            if not rendered:
                break
        lines.append(separator + rendered if separator else rendered)
        current_length += len(lines[-1])
        if current_length >= max_chars:
            break
    return "".join(lines)


def build_collection_context(question: str, collection_keys: list[str]) -> str:
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
    max_context_chars = runtime_service.get_max_context_chars()
    return format_docs_with_limit(docs[:max_docs], max_chars=max_context_chars)


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
