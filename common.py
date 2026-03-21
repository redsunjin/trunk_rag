"""Shared utilities for the W2_007 markdown-header RAG project."""

from __future__ import annotations

import logging
import json
import os
import re
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Iterable

from dotenv import load_dotenv
from langchain_core.documents import Document
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.runnables import RunnableLambda
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
EMBEDDING_DEVICE_ENV_KEY = "DOC_RAG_EMBEDDING_DEVICE"
DEFAULT_OLLAMA_HTTP_TIMEOUT_SECONDS = 120
TOKEN_FALLBACK_PATTERN = re.compile(r"[가-힣]|[A-Za-z0-9_]+|[^\s]")

logger = logging.getLogger("doc_rag.common")


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
    kwargs: dict[str, Any] = {"model_name": model_name}
    device = os.getenv(EMBEDDING_DEVICE_ENV_KEY, "").strip()
    if device:
        kwargs["model_kwargs"] = {"device": device}
    return embeddings_cls(**kwargs)


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
    if value not in {"openai", "ollama", "lmstudio", "groq"}:
        raise ValueError(f"Unsupported provider: {provider}")
    return value


def default_llm_model(provider: str) -> str:
    value = normalize_provider(provider)
    defaults = {
        "openai": "gpt-4o-mini",
        "ollama": "qwen3:4b",
        "lmstudio": "local-model",
        "groq": "groq-model",
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
    elif value == "groq":
        api_key_value = api_key_value or os.getenv("GROQ_API_KEY")
        base_url_value = base_url_value or os.getenv("GROQ_BASE_URL") or "https://api.groq.com/openai/v1"
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

    if provider == "groq":
        if ChatOpenAI is None:
            raise ImportError("`langchain-openai` is not installed.")
        if not api_key:
            raise ValueError("GROQ_API_KEY is required for groq provider.")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key,
            openai_api_base=base_url or "https://api.groq.com/openai/v1",
        )

    if provider == "lmstudio":
        if ChatOpenAI is None:
            raise ImportError("`langchain-openai` is not installed.")
        return ChatOpenAI(
            model=model,
            temperature=temperature,
            openai_api_key=api_key or "lm-studio",
            openai_api_base=base_url or "http://localhost:1234/v1",
        )

    return build_ollama_chat_runnable(
        model=model,
        temperature=temperature,
        base_url=base_url or "http://localhost:11434",
    )


def _message_role(message: BaseMessage) -> str:
    if message.type == "system":
        return "system"
    if message.type == "ai":
        return "assistant"
    return "user"


def _message_content(message: BaseMessage) -> str:
    content = message.content
    if isinstance(content, str):
        return content
    return str(content)


def build_ollama_messages(prompt: Any) -> list[dict[str, str]]:
    if hasattr(prompt, "to_messages"):
        messages = prompt.to_messages()
    elif isinstance(prompt, list) and all(isinstance(item, BaseMessage) for item in prompt):
        messages = prompt
    else:
        messages = [HumanMessage(content=str(prompt))]

    payload: list[dict[str, str]] = []
    for message in messages:
        payload.append(
            {
                "role": _message_role(message),
                "content": _message_content(message),
            }
        )
    return payload


def build_ollama_response_message(payload: dict[str, Any]) -> AIMessage:
    message = payload.get("message", {})
    if not isinstance(message, dict):
        return AIMessage(content=str(message))

    content = str(message.get("content") or "").strip()
    if not content:
        content = str(message.get("thinking") or "").strip()

    extra = {
        key: value
        for key, value in message.items()
        if key not in {"content"}
    }
    return AIMessage(content=content, additional_kwargs=extra)


def invoke_ollama_chat(
    prompt: Any,
    *,
    model: str,
    temperature: float,
    base_url: str,
) -> AIMessage:
    num_predict = parse_optional_positive_int_env(OLLAMA_NUM_PREDICT_ENV_KEY)
    options: dict[str, Any] = {"temperature": temperature}
    if num_predict is not None:
        options["num_predict"] = num_predict

    body = {
        "model": model,
        "messages": build_ollama_messages(prompt),
        "stream": False,
        "options": options,
    }
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/api/chat",
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=DEFAULT_OLLAMA_HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP error: {exc.code} {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Ollama connection failed: {exc}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError("Ollama returned invalid JSON.") from exc
    return build_ollama_response_message(payload)


def build_ollama_chat_runnable(
    *,
    model: str,
    temperature: float,
    base_url: str,
):
    return RunnableLambda(
        lambda prompt: invoke_ollama_chat(
            prompt,
            model=model,
            temperature=temperature,
            base_url=base_url,
        )
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
    try:
        return RecursiveCharacterTextSplitter.from_tiktoken_encoder(
            encoding_name=encoding,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
        )
    except Exception as exc:
        logger.warning(
            "token splitter fallback to approximate token counter: encoding=%s error=%s",
            encoding,
            exc,
        )
        return RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=approximate_token_count,
        )


def approximate_token_count(text: str) -> int:
    tokens = TOKEN_FALLBACK_PATTERN.findall(text)
    return max(len(tokens), 1)


def count_text_tokens(text: str, encoding_name: str = DEFAULT_TOKEN_ENCODING) -> int:
    try:
        import tiktoken

        encoder = tiktoken.get_encoding(encoding_name)
        return max(len(encoder.encode(text)), 1)
    except Exception as exc:
        logger.warning(
            "token count fallback to approximate counter: encoding=%s error=%s",
            encoding_name,
            exc,
        )
        return approximate_token_count(text)


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
