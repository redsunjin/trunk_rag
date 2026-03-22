from __future__ import annotations

import logging
import os
from pathlib import Path
from datetime import datetime, timezone

from fastapi import HTTPException

from common import (
    CHUNKING_MODE_CHAR,
    DEFAULT_TOKEN_ENCODING,
    default_llm_model,
    normalize_chunking_mode,
    normalize_provider,
    resolve_llm_config,
)
from core.settings import (
    ADMIN_CODE_ENV_KEY,
    AUTO_APPROVE_ENV_KEY,
    CHUNK_TOKEN_ENCODING_ENV_KEY,
    CHUNKING_MODE_ENV_KEY,
    DEFAULT_MAX_CONTEXT_CHARS,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    DEFAULT_EMBEDDING_MODEL,
    EMBEDDING_MODEL_ENV_KEY,
    MAX_CONTEXT_CHARS_ENV_KEY,
    QUERY_TIMEOUT_SECONDS_ENV_KEY,
)

logger = logging.getLogger("doc_rag.api")


def get_admin_code() -> str:
    value = os.getenv(ADMIN_CODE_ENV_KEY, "admin1234").strip()
    return value or "admin1234"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def parse_bool_env(name: str, default: bool = False) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on", "y"}


def is_auto_approve_enabled() -> bool:
    return parse_bool_env(AUTO_APPROVE_ENV_KEY, default=False)


def get_query_timeout_seconds() -> int:
    raw = os.getenv(QUERY_TIMEOUT_SECONDS_ENV_KEY, str(DEFAULT_QUERY_TIMEOUT_SECONDS))
    try:
        timeout_seconds = int(str(raw).strip())
    except (TypeError, ValueError):
        logger.warning(
            "invalid query timeout: %s (fallback=%s)",
            raw,
            DEFAULT_QUERY_TIMEOUT_SECONDS,
        )
        return DEFAULT_QUERY_TIMEOUT_SECONDS

    if timeout_seconds < 1:
        logger.warning(
            "query timeout must be >= 1: %s (fallback=%s)",
            timeout_seconds,
            DEFAULT_QUERY_TIMEOUT_SECONDS,
        )
        return DEFAULT_QUERY_TIMEOUT_SECONDS

    return timeout_seconds


def get_max_context_chars() -> int | None:
    raw = os.getenv(MAX_CONTEXT_CHARS_ENV_KEY)
    if raw is None:
        return DEFAULT_MAX_CONTEXT_CHARS
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        logger.warning("invalid max context chars: %s (fallback=%s)", raw, DEFAULT_MAX_CONTEXT_CHARS)
        return DEFAULT_MAX_CONTEXT_CHARS
    if value <= 0:
        logger.warning("max context chars must be > 0: %s (fallback=%s)", value, DEFAULT_MAX_CONTEXT_CHARS)
        return DEFAULT_MAX_CONTEXT_CHARS
    return value


def get_chunking_config() -> dict[str, str]:
    raw_mode = os.getenv(CHUNKING_MODE_ENV_KEY, CHUNKING_MODE_CHAR)
    try:
        mode = normalize_chunking_mode(raw_mode)
    except ValueError:
        logger.warning(
            "invalid chunking mode: %s (fallback=%s)",
            raw_mode,
            CHUNKING_MODE_CHAR,
        )
        mode = CHUNKING_MODE_CHAR

    token_encoding = os.getenv(CHUNK_TOKEN_ENCODING_ENV_KEY, DEFAULT_TOKEN_ENCODING).strip()
    if not token_encoding:
        token_encoding = DEFAULT_TOKEN_ENCODING
    return {"mode": mode, "token_encoding": token_encoding}


def get_default_llm_config() -> dict[str, str | None]:
    raw_provider = os.getenv("LLM_PROVIDER", "ollama")
    try:
        provider = normalize_provider(raw_provider)
    except ValueError:
        logger.warning("invalid default llm provider: %s (fallback=ollama)", raw_provider)
        provider = "ollama"

    raw_model = os.getenv("LLM_MODEL")
    model = (raw_model or "").strip() or default_llm_model(provider)
    provider, model, _api_key, base_url = resolve_llm_config(
        provider=provider,
        model=model,
    )
    return {
        "provider": provider,
        "model": model,
        "base_url": base_url,
    }


def get_embedding_model() -> str:
    value = os.getenv(EMBEDDING_MODEL_ENV_KEY, DEFAULT_EMBEDDING_MODEL).strip()
    return value or DEFAULT_EMBEDDING_MODEL


def is_local_path_like(value: str) -> bool:
    expanded = Path(value).expanduser()
    return expanded.is_absolute() or value.startswith(".") or value.startswith("~")


def build_release_web_guidance(
    *,
    vectors: int,
    default_llm_provider: str,
    default_llm_model: str | None,
    default_llm_base_url: str | None,
    embedding_model: str,
) -> dict[str, object]:
    steps = [
        "기본 시작 경로는 `run_doc_rag.bat` 하나로 유지합니다.",
    ]
    status = "ready"
    headline = "기본 웹 MVP 경로로 바로 사용할 수 있습니다."

    if default_llm_provider == "ollama":
        target_model = default_llm_model or "llama3.1:8b"
        base_url = (default_llm_base_url or "http://localhost:11434").strip() or "http://localhost:11434"
        steps.append(f"Ollama를 `{base_url}`에서 실행하고 기본 모델 `{target_model}`을 준비하세요.")
    elif default_llm_provider == "groq":
        target_model = default_llm_model or "groq-model"
        base_url = (default_llm_base_url or "https://api.groq.com/openai/v1").strip() or "https://api.groq.com/openai/v1"
        steps.append(
            f"Groq API를 `{base_url}`로 사용하고 `.env`의 `GROQ_API_KEY`와 `LLM_MODEL`을 실제 값으로 설정하세요."
        )
    elif default_llm_provider == "lmstudio":
        target_model = default_llm_model or "local-model"
        base_url = (default_llm_base_url or "http://localhost:1234/v1").strip() or "http://localhost:1234/v1"
        if target_model == "local-model":
            steps.append(
                f"LM Studio 서버를 `{base_url}`에서 실행하고, 현재 로드한 모델명을 `.env`의 `LLM_MODEL`에 반영하세요."
            )
        else:
            steps.append(f"LM Studio 서버를 `{base_url}`에서 실행하고 기본 모델 `{target_model}`을 준비하세요.")
    else:
        steps.append("기본 LLM provider 설정과 연결 상태를 `/intro`에서 먼저 확인하세요.")

    if not is_local_path_like(embedding_model) and embedding_model == DEFAULT_EMBEDDING_MODEL:
        steps.append(
            "오프라인 환경이면 `DOC_RAG_EMBEDDING_MODEL`에 로컬 임베딩 경로를 지정하거나 HuggingFace cache를 준비하세요."
        )

    if vectors <= 0:
        status = "needs_reindex"
        headline = "질의 전에 먼저 인덱싱이 필요합니다."
        steps.append("`/app`에서 Reindex를 실행하거나 `.venv\\Scripts\\python.exe build_index.py --reset`을 실행하세요.")
    else:
        steps.append("`/intro -> /app` 경로로 진입해 바로 질의할 수 있습니다.")

    steps.append("실패 시 `/intro`의 상태 메시지와 request_id를 기준으로 원인을 확인하세요.")
    return {
        "status": status,
        "headline": headline,
        "steps": steps,
    }


def verify_admin_code(code: str) -> None:
    if code.strip() != get_admin_code():
        raise HTTPException(status_code=401, detail="관리자 인증코드가 올바르지 않습니다.")


def sanitize_source_name(source_name: str) -> str:
    value = source_name.strip()
    if not value:
        raise ValueError("source_name is empty")
    safe = "".join(char if (char.isalnum() or char in {"_", "-", "."}) else "_" for char in value)
    if not safe.lower().endswith(".md"):
        safe = f"{safe}.md"
    return safe


def sanitize_doc_key(doc_key: str) -> str:
    value = doc_key.strip().lower()
    if value.endswith(".md"):
        value = value[:-3]
    if not value:
        raise ValueError("doc_key is empty")
    safe = "".join(char if (char.isalnum() or char in {"_", "-"}) else "_" for char in value)
    safe = safe.strip("_")
    if not safe:
        raise ValueError("doc_key is empty")
    return safe
