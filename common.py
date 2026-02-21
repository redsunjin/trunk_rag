"""Shared utilities for the W2_007 markdown-header RAG project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover
    from langchain_community.embeddings import HuggingFaceEmbeddings  # type: ignore

try:
    from langchain_openai import ChatOpenAI
except ImportError:  # pragma: no cover
    ChatOpenAI = None  # type: ignore[assignment]

try:
    from langchain_ollama import ChatOllama
except ImportError:  # pragma: no cover
    try:
        from langchain_community.chat_models import ChatOllama  # type: ignore[no-redef]
    except ImportError:  # pragma: no cover
        ChatOllama = None  # type: ignore[assignment]

DEFAULT_FILE_NAMES = [
    "eu_summry.md",
    "fr.md",
    "ge.md",
    "it.md",
    "uk.md",
]

COUNTRY_BY_STEM = {
    "eu_summry": "all",
    "fr": "france",
    "ge": "germany",
    "it": "italy",
    "uk": "uk",
}


def project_root() -> Path:
    return Path(__file__).resolve().parent


def load_project_env() -> Path | None:
    """Load .env from project root if present."""
    env_path = project_root() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)
        return env_path
    return None


def default_data_dir() -> Path:
    return project_root() / "data"


def default_persist_dir() -> Path:
    return project_root() / "chroma_db"


def create_embeddings(model_name: str) -> HuggingFaceEmbeddings:
    return HuggingFaceEmbeddings(model_name=model_name)


def normalize_provider(provider: str) -> str:
    value = provider.strip().lower()
    if value not in {"openai", "ollama", "lmstudio"}:
        raise ValueError(f"Unsupported provider: {provider}")
    return value


def default_llm_model(provider: str) -> str:
    value = normalize_provider(provider)
    defaults = {
        "openai": "gpt-4o-mini",
        "ollama": "qwen3:4b",
        "lmstudio": "local-model",
    }
    return defaults[value]


def resolve_llm_config(
    provider: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
) -> tuple[str, str, str | None, str | None]:
    value = normalize_provider(provider)

    model_value = (model or os.getenv("LLM_MODEL") or default_llm_model(value)).strip()

    api_key_value = (api_key or "").strip() or None
    base_url_value = (base_url or "").strip() or None

    if value == "openai":
        api_key_value = api_key_value or os.getenv("OPENAI_API_KEY")
        base_url_value = base_url_value or os.getenv("OPENAI_API_BASE")
    elif value == "lmstudio":
        api_key_value = api_key_value or os.getenv("LMSTUDIO_API_KEY") or "lm-studio"
        base_url_value = base_url_value or os.getenv("LMSTUDIO_BASE_URL") or "http://localhost:1234/v1"
    else:
        base_url_value = base_url_value or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434"

    return value, model_value, api_key_value, base_url_value


def create_chat_llm(
    provider: str,
    model: str | None = None,
    temperature: float = 0.0,
    api_key: str | None = None,
    base_url: str | None = None,
):
    provider, model, api_key, base_url = resolve_llm_config(
        provider=provider,
        model=model,
        api_key=api_key,
        base_url=base_url,
    )

    if provider == "openai":
        if ChatOpenAI is None:
            raise ImportError("`langchain-openai` is not installed.")
        kwargs = {"model": model, "temperature": temperature}
        if api_key:
            kwargs["openai_api_key"] = api_key
        if base_url:
            kwargs["openai_api_base"] = base_url
        return ChatOpenAI(**kwargs)

    if provider == "lmstudio":
        if ChatOpenAI is None:
            raise ImportError("`langchain-openai` is not installed.")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key or "lm-studio",
            openai_api_base=base_url or "http://localhost:1234/v1",
        )

    if ChatOllama is None:
        raise ImportError("`ChatOllama` backend is not available. Install `langchain-ollama`.")
    return ChatOllama(
        model=model,
        temperature=temperature,
        base_url=base_url or "http://localhost:11434",
    )


def load_markdown_documents(data_dir: Path, file_names: Iterable[str]) -> list[Document]:
    docs: list[Document] = []

    for name in file_names:
        path = data_dir / name
        if not path.exists():
            print(f"[skip] missing file: {path}")
            continue

        text = path.read_text(encoding="utf-8")
        stem = path.stem

        docs.append(
            Document(
                page_content=text,
                metadata={
                    "source": path.name,
                    "topic": "europe_science_history",
                    "country": COUNTRY_BY_STEM.get(stem, "unknown"),
                    "doc_type": "summary" if stem == "eu_summry" else "country",
                },
            )
        )

    return docs


def split_by_markdown_headers(
    docs: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "h2"), ("###", "h3"), ("####", "h4")],
        strip_headers=False,
    )
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    chunks: list[Document] = []
    for doc in docs:
        header_docs = header_splitter.split_text(doc.page_content)
        if not header_docs:
            header_docs = [Document(page_content=doc.page_content, metadata={})]

        for part in header_docs:
            part.metadata = {**doc.metadata, **part.metadata}

        chunks.extend(char_splitter.split_documents(header_docs))

    return chunks
