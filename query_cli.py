from __future__ import annotations

import argparse

from langchain_chroma import Chroma
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

from common import (
    create_chat_llm,
    create_embeddings,
    default_persist_dir,
    load_project_env,
    resolve_llm_config,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Query the markdown-header RAG index.")
    parser.add_argument("query", type=str, nargs="?", default="각 국가별 대표적인 과학적인 성과를 요약해줘")
    parser.add_argument("--persist-dir", type=str, default=str(default_persist_dir()))
    parser.add_argument("--collection", type=str, default="w2_007_header_rag")
    parser.add_argument("--embedding-model", type=str, default="BAAI/bge-m3")
    parser.add_argument("--llm-provider", type=str, default="openai", choices=["openai", "ollama", "lmstudio"])
    parser.add_argument("--llm-model", "--llm", dest="llm_model", type=str, default=None)
    parser.add_argument("--llm-api-key", type=str, default=None)
    parser.add_argument("--llm-base-url", type=str, default=None)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--k", type=int, default=3)
    parser.add_argument("--show-docs", action="store_true")
    return parser.parse_args()


def format_docs(docs) -> str:
    lines = []
    for idx, doc in enumerate(docs, 1):
        source = doc.metadata.get("source", "unknown")
        h2 = doc.metadata.get("h2", "")
        lines.append(f"[{idx}] source={source} h2={h2}\n{doc.page_content}")
    return "\n\n".join(lines)


def main() -> None:
    args = parse_args()
    env_path = load_project_env()
    if env_path:
        print(f"Loaded env: {env_path}")

    embeddings = create_embeddings(args.embedding_model)
    db = Chroma(
        collection_name=args.collection,
        embedding_function=embeddings,
        persist_directory=args.persist_dir,
    )

    retriever = db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": args.k, "fetch_k": 10, "lambda_mult": 0.3},
    )

    prompt = ChatPromptTemplate.from_template(
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

    provider, model, api_key, base_url = resolve_llm_config(
        provider=args.llm_provider,
        model=args.llm_model,
        api_key=args.llm_api_key,
        base_url=args.llm_base_url,
    )

    print(f"[LLM] provider={provider} model={model}")
    if base_url:
        print(f"[LLM] base_url={base_url}")

    llm = create_chat_llm(
        provider=provider,
        model=model,
        temperature=args.temperature,
        api_key=api_key,
        base_url=base_url,
    )

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    if args.show_docs:
        docs = retriever.invoke(args.query)
        print("\n[Retrieved Docs]")
        print(format_docs(docs)[:2500])

    output = rag_chain.invoke(args.query)
    print("\n[Query]")
    print(args.query)
    print("\n[Answer]")
    print(output)


if __name__ == "__main__":
    main()
