from __future__ import annotations

import logging
import os
from datetime import UTC, datetime

from fastapi import HTTPException

from common import CHUNKING_MODE_CHAR, DEFAULT_TOKEN_ENCODING, normalize_chunking_mode
from core.settings import (
    ADMIN_CODE_ENV_KEY,
    AUTO_APPROVE_ENV_KEY,
    CHUNK_TOKEN_ENCODING_ENV_KEY,
    CHUNKING_MODE_ENV_KEY,
    DEFAULT_QUERY_TIMEOUT_SECONDS,
    MAX_CONTEXT_CHARS_ENV_KEY,
    QUERY_TIMEOUT_SECONDS_ENV_KEY,
)

logger = logging.getLogger("doc_rag.api")


def get_admin_code() -> str:
    value = os.getenv(ADMIN_CODE_ENV_KEY, "admin1234").strip()
    return value or "admin1234"


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


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
        return None
    try:
        value = int(raw.strip())
    except (TypeError, ValueError):
        logger.warning("invalid max context chars: %s (ignored)", raw)
        return None
    if value <= 0:
        logger.warning("max context chars must be > 0: %s (ignored)", value)
        return None
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
