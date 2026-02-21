from __future__ import annotations

import os
from typing import Iterator

import gradio as gr
from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from common import (
    create_chat_llm,
    create_embeddings,
    default_llm_model,
    default_persist_dir,
    load_project_env,
    resolve_llm_config,
)


def format_docs(docs) -> str:
    lines = []
    for idx, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        h2 = doc.metadata.get("h2", "")
        lines.append(f"[{idx}] source={source} h2={h2}\n{doc.page_content}")
    return "\n\n".join(lines)


def build_retriever():
    embeddings = create_embeddings("BAAI/bge-m3")
    db = Chroma(
        collection_name="w2_007_header_rag",
        embedding_function=embeddings,
        persist_directory=str(default_persist_dir()),
    )

    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 3, "fetch_k": 10, "lambda_mult": 0.3},
    )
    return retriever


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


def build_chain(provider: str, model: str, api_key: str, base_url: str):
    provider, model, api_key, base_url = resolve_llm_config(
        provider=provider,
        model=model or default_llm_model(provider),
        api_key=api_key,
        base_url=base_url,
    )
    llm = create_chat_llm(
        provider=provider,
        model=model,
        temperature=0.0,
        api_key=api_key,
        base_url=base_url,
    )
    chain = (
        {"context": RETRIEVER | format_docs, "question": RunnablePassthrough()}
        | PROMPT
        | llm
        | StrOutputParser()
    )
    return chain


def get_streaming_response(
    message: str,
    history,
    provider: str,
    model: str,
    api_key: str,
    base_url: str,
) -> Iterator[str]:
    if not message.strip():
        yield "질문을 입력해 주세요."
        return

    try:
        rag_chain = build_chain(provider=provider, model=model, api_key=api_key, base_url=base_url)
    except Exception as exc:  # pragma: no cover
        yield f"LLM 초기화 오류: {exc}"
        return

    response = ""
    for chunk in rag_chain.stream(message):
        if isinstance(chunk, str):
            response += chunk
            yield response


def main() -> None:
    default_provider = os.getenv("LLM_PROVIDER", "openai").strip().lower()
    if default_provider not in {"openai", "ollama", "lmstudio"}:
        default_provider = "openai"

    default_model = os.getenv("LLM_MODEL") or default_llm_model(default_provider)
    if default_provider == "ollama":
        default_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    elif default_provider == "lmstudio":
        default_base_url = os.getenv("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
    else:
        default_base_url = os.getenv("OPENAI_API_BASE", "")

    demo = gr.ChatInterface(
        fn=get_streaming_response,
        title="W2_007 Header-based RAG",
        description="##/###/#### 헤더 기준 청킹 + MMR 검색 (OpenAI / Ollama / LM Studio 선택 가능)",
        additional_inputs=[
            gr.Dropdown(
                choices=["openai", "ollama", "lmstudio"],
                value=default_provider,
                label="LLM Provider",
            ),
            gr.Textbox(
                value=default_model,
                label="LLM Model",
                placeholder="예: gpt-4o-mini / qwen2.5:7b-instruct / lmstudio 모델명",
            ),
            gr.Textbox(
                value="",
                type="password",
                label="API Key (optional)",
                placeholder="OpenAI 또는 LM Studio 키 입력 (없으면 .env 사용)",
            ),
            gr.Textbox(
                value=default_base_url,
                label="Base URL (optional)",
                placeholder="예: http://localhost:11434 또는 http://localhost:1234/v1",
            ),
        ],
        examples=[
            "각 국가별 대표적인 과학적 성과를 요약해줘",
            "프랑스와 독일의 근대 과학 발전 차이를 알려줘",
        ],
    )
    demo.launch()


ENV_PATH = load_project_env()
if ENV_PATH:
    print(f"Loaded env: {ENV_PATH}")

RETRIEVER = build_retriever()


if __name__ == "__main__":
    main()
