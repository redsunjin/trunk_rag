"""Shared utilities for the W2_007 markdown-header RAG project."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter

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

CHUNKING_MODE_CHAR = "char"
CHUNKING_MODE_TOKEN = "token"
SUPPORTED_CHUNKING_MODES = {CHUNKING_MODE_CHAR, CHUNKING_MODE_TOKEN}
DEFAULT_TOKEN_ENCODING = "cl100k_base"
OLLAMA_NUM_PREDICT_ENV_KEY = "DOC_RAG_OLLAMA_NUM_PREDICT"


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


def resolve_hf_embeddings_class():
    try:
        from langchain_huggingface import HuggingFaceEmbeddings as cls

        return cls
    except Exception:  # pragma: no cover
        from langchain_community.embeddings import HuggingFaceEmbeddings as cls  # type: ignore

        return cls


def create_embeddings(model_name: str) -> Any:
    embeddings_cls = resolve_hf_embeddings_class()
    return embeddings_cls(model_name=model_name)


def parse_optional_positive_int_env(name: str) -> int | None:
    raw = os.getenv(name)
    if raw is None:
        return None
    try:
        value = int(raw.strip())
    except ValueError:
        return None
    if value <= 0:
        return None
    return value


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
    kwargs: dict[str, Any] = {
        "model": model,
        "temperature": temperature,
        "base_url": base_url or "http://localhost:11434",
    }
    num_predict = parse_optional_positive_int_env(OLLAMA_NUM_PREDICT_ENV_KEY)
    if num_predict is not None:
        kwargs["num_predict"] = num_predict
    return ChatOllama(**kwargs)


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


def normalize_chunking_mode(chunking_mode: str | None) -> str:
    value = (chunking_mode or CHUNKING_MODE_CHAR).strip().lower()
    if value not in SUPPORTED_CHUNKING_MODES:
        supported = ", ".join(sorted(SUPPORTED_CHUNKING_MODES))
        raise ValueError(f"Unsupported chunking mode: {chunking_mode}. Use one of: {supported}")
    return value


def build_text_splitter(
    *,
    chunk_size: int,
    chunk_overlap: int,
    chunking_mode: str = CHUNKING_MODE_CHAR,
    token_encoding: str = DEFAULT_TOKEN_ENCODING,
) -> RecursiveCharacterTextSplitter:
    mode = normalize_chunking_mode(chunking_mode)
    if mode == CHUNKING_MODE_CHAR:
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )

    encoding = token_encoding.strip() or DEFAULT_TOKEN_ENCODING
    return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
        encoding_name=encoding,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )


def split_by_markdown_headers(
    docs: list[Document],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
    chunking_mode: str = CHUNKING_MODE_CHAR,
    token_encoding: str = DEFAULT_TOKEN_ENCODING,
) -> list[Document]:
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("##", "h2"), ("###", "h3"), ("####", "h4")],
        strip_headers=False,
    )
    text_splitter = build_text_splitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        chunking_mode=chunking_mode,
        token_encoding=token_encoding,
    )

    chunks: list[Document] = []
    for doc in docs:
        header_docs = header_splitter.split_text(doc.page_content)
        if not header_docs:
            header_docs = [Document(page_content=doc.page_content, metadata={})]

        for part in header_docs:
            part.metadata = {**doc.metadata, **part.metadata}

        chunks.extend(text_splitter.split_documents(header_docs))

    return chunks
