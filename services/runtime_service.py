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
    SEARCH_FETCH_K,
    SEARCH_K,
    MAX_CONTEXT_CHARS_ENV_KEY,
    QUERY_TIMEOUT_SECONDS_ENV_KEY,
)

logger = logging.getLogger("doc_rag.api")

RUNTIME_PROFILE_VERIFIED = "verified"
RUNTIME_PROFILE_EXPERIMENTAL = "experimental"
RUNTIME_PROFILE_NOT_RECOMMENDED = "not_recommended"
VERIFIED_LOCAL_OLLAMA_MODEL = "llama3.1:8b"
VERIFIED_LOCAL_OLLAMA_TIMEOUT_SECONDS = 30
VERIFIED_GROQ_MODEL = "llama-3.1-8b-instant"

NOT_RECOMMENDED_RUNTIME_MODELS: dict[str, set[str]] = {
    "ollama": {
        "qwen3:4b",
        "qwen3.5:4b",
        "qwen3.5:9b",
        "gemma3:12b",
    },
    "lmstudio": {
        "qwen3.5-2b-mlx-4bit",
        "qwen3.5-4b-mlx-4bit",
    },
}

GENERATION_BUDGET_STANDARD = "standard"
GENERATION_BUDGET_COMPACT = "compact"
GENERATION_BUDGET_RESTRICTED = "restricted"
GENERATION_BUDGET_CLOUD_BALANCED = "cloud_balanced"


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
    if not raw.strip():
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


def build_runtime_profile(
    *,
    provider: str,
    model: str | None,
    timeout_seconds: int,
) -> dict[str, object]:
    normalized_provider = normalize_provider(provider)
    normalized_model = (model or "").strip()

    if normalized_provider == "groq" and normalized_model == VERIFIED_GROQ_MODEL:
        return {
            "status": RUNTIME_PROFILE_VERIFIED,
            "scope": "cloud",
            "message": (
                "현재 Groq 런타임 프로파일은 ops-baseline 실측에서 검증됐습니다."
            ),
            "recommendation": "운영 안정성과 지연시간 기준으로 현재 가장 권장되는 경로입니다.",
        }

    if normalized_provider == "ollama" and normalized_model == VERIFIED_LOCAL_OLLAMA_MODEL:
        if timeout_seconds >= VERIFIED_LOCAL_OLLAMA_TIMEOUT_SECONDS:
            return {
                "status": RUNTIME_PROFILE_VERIFIED,
                "scope": "local",
                "message": (
                    "현재 Ollama 런타임 프로파일은 로컬 ops-baseline 실측에서 검증됐습니다."
                ),
                "recommendation": (
                    f"`DOC_RAG_QUERY_TIMEOUT_SECONDS={VERIFIED_LOCAL_OLLAMA_TIMEOUT_SECONDS}` 이상을 유지하세요."
                ),
            }
        return {
            "status": RUNTIME_PROFILE_EXPERIMENTAL,
            "scope": "local",
            "message": (
                "모델은 검증된 로컬 후보지만 현재 timeout이 낮아 운영 게이트 재현 가능성이 떨어집니다."
            ),
            "recommendation": (
                f"`{VERIFIED_LOCAL_OLLAMA_MODEL}`를 유지하고 "
                f"`DOC_RAG_QUERY_TIMEOUT_SECONDS={VERIFIED_LOCAL_OLLAMA_TIMEOUT_SECONDS}` 이상으로 올리세요."
            ),
        }

    if normalized_model and normalized_model in NOT_RECOMMENDED_RUNTIME_MODELS.get(normalized_provider, set()):
        recommendation = (
            f"로컬 기본 경로는 `{VERIFIED_LOCAL_OLLAMA_MODEL}` + "
            f"`DOC_RAG_QUERY_TIMEOUT_SECONDS={VERIFIED_LOCAL_OLLAMA_TIMEOUT_SECONDS}`를 권장합니다."
        )
        if normalized_provider == "groq":
            recommendation = f"클라우드 운영은 `{VERIFIED_GROQ_MODEL}` 경로를 우선 검토하세요."
        return {
            "status": RUNTIME_PROFILE_NOT_RECOMMENDED,
            "scope": "local" if normalized_provider in {"ollama", "lmstudio"} else "cloud",
            "message": "현재 런타임 프로파일은 local ops-baseline 실측에서 반복 실패한 모델 조합입니다.",
            "recommendation": recommendation,
        }

    scope = "local" if normalized_provider in {"ollama", "lmstudio"} else "cloud"
    if normalized_provider == "groq":
        recommendation = f"운영 검증 기준은 `{VERIFIED_GROQ_MODEL}`입니다."
    elif normalized_provider == "ollama":
        recommendation = (
            f"로컬 기본 운영은 `{VERIFIED_LOCAL_OLLAMA_MODEL}` + "
            f"`DOC_RAG_QUERY_TIMEOUT_SECONDS={VERIFIED_LOCAL_OLLAMA_TIMEOUT_SECONDS}`를 먼저 기준으로 삼으세요."
        )
    else:
        recommendation = "현재 provider/model 조합은 연결 가능 여부와 별도로 ops-baseline 실측이 필요합니다."

    return {
        "status": RUNTIME_PROFILE_EXPERIMENTAL,
        "scope": scope,
        "message": "현재 런타임 프로파일은 연결 가능 여부만 확인됐고 운영 게이트는 아직 미검증입니다.",
        "recommendation": recommendation,
    }


def _bounded_context_limit(target: int) -> int:
    return min(get_max_context_chars() or DEFAULT_MAX_CONTEXT_CHARS, target)


def _build_budget_summary(
    *,
    profile_name: str,
    per_collection_k: int,
    per_collection_fetch_k: int,
    max_total_docs: int,
    max_context_chars: int,
    generation_budget_profile: str,
    max_output_tokens: int | None,
) -> str:
    output_text = "-" if max_output_tokens is None else str(max_output_tokens)
    return (
        f"profile={profile_name} | k={per_collection_k} | fetch_k={per_collection_fetch_k} | "
        f"max_docs={max_total_docs} | context={max_context_chars} | "
        f"generation={generation_budget_profile} | max_output_tokens={output_text}"
    )


def plan_query_budget(
    *,
    provider: str,
    model: str | None,
    timeout_seconds: int,
    collection_count: int,
    route_reason: str,
) -> dict[str, object]:
    runtime_profile = build_runtime_profile(
        provider=provider,
        model=model,
        timeout_seconds=timeout_seconds,
    )
    is_multi = collection_count > 1 or "multi" in route_reason
    default_context = get_max_context_chars() or DEFAULT_MAX_CONTEXT_CHARS

    if runtime_profile["status"] == RUNTIME_PROFILE_VERIFIED and runtime_profile["scope"] == "local":
        if is_multi:
            profile_name = "verified_local_multi"
            per_collection_k = 2
            per_collection_fetch_k = 4
            max_total_docs = 4
            max_context_chars = min(default_context, 1200)
            generation_budget_profile = GENERATION_BUDGET_COMPACT
            max_output_tokens = 160
        else:
            profile_name = "verified_local_single"
            per_collection_k = SEARCH_K
            per_collection_fetch_k = SEARCH_FETCH_K
            max_total_docs = SEARCH_K
            max_context_chars = default_context
            generation_budget_profile = GENERATION_BUDGET_STANDARD
            max_output_tokens = 192
    elif runtime_profile["status"] == RUNTIME_PROFILE_VERIFIED and runtime_profile["scope"] == "cloud":
        if is_multi:
            profile_name = "verified_cloud_multi"
            per_collection_k = 2
            per_collection_fetch_k = 5
            max_total_docs = 4
            max_context_chars = min(default_context, 1600)
            generation_budget_profile = GENERATION_BUDGET_CLOUD_BALANCED
            max_output_tokens = 224
        else:
            profile_name = "verified_cloud_single"
            per_collection_k = SEARCH_K
            per_collection_fetch_k = SEARCH_FETCH_K
            max_total_docs = SEARCH_K
            max_context_chars = min(default_context, 1800)
            generation_budget_profile = GENERATION_BUDGET_CLOUD_BALANCED
            max_output_tokens = 256
    elif runtime_profile["status"] == RUNTIME_PROFILE_NOT_RECOMMENDED and runtime_profile["scope"] == "local":
        profile_name = "not_recommended_local"
        per_collection_k = 1
        per_collection_fetch_k = 2 if is_multi else 3
        max_total_docs = 2 if is_multi else 1
        max_context_chars = _bounded_context_limit(700 if is_multi else 900)
        generation_budget_profile = GENERATION_BUDGET_RESTRICTED
        max_output_tokens = 96
    elif runtime_profile["scope"] == "local":
        if is_multi:
            profile_name = "experimental_local_multi"
            per_collection_k = 1
            per_collection_fetch_k = 3
            max_total_docs = 2
            max_context_chars = _bounded_context_limit(900)
            generation_budget_profile = GENERATION_BUDGET_RESTRICTED
            max_output_tokens = 128
        else:
            profile_name = "experimental_local_single"
            per_collection_k = 2
            per_collection_fetch_k = 6
            max_total_docs = 2
            max_context_chars = _bounded_context_limit(1200)
            generation_budget_profile = GENERATION_BUDGET_COMPACT
            max_output_tokens = 160
    else:
        if is_multi:
            profile_name = "experimental_cloud_multi"
            per_collection_k = 2
            per_collection_fetch_k = 5
            max_total_docs = 4
            max_context_chars = min(default_context, 1500)
            generation_budget_profile = GENERATION_BUDGET_CLOUD_BALANCED
            max_output_tokens = 192
        else:
            profile_name = "experimental_cloud_single"
            per_collection_k = SEARCH_K
            per_collection_fetch_k = SEARCH_FETCH_K
            max_total_docs = SEARCH_K
            max_context_chars = min(default_context, 1600)
            generation_budget_profile = GENERATION_BUDGET_CLOUD_BALANCED
            max_output_tokens = 224

    summary = _build_budget_summary(
        profile_name=profile_name,
        per_collection_k=per_collection_k,
        per_collection_fetch_k=per_collection_fetch_k,
        max_total_docs=max_total_docs,
        max_context_chars=max_context_chars,
        generation_budget_profile=generation_budget_profile,
        max_output_tokens=max_output_tokens,
    )
    return {
        "profile": profile_name,
        "summary": summary,
        "runtime_profile": runtime_profile,
        "collection_count": collection_count,
        "route_reason": route_reason,
        "per_collection_k": per_collection_k,
        "per_collection_fetch_k": per_collection_fetch_k,
        "max_total_docs": max_total_docs,
        "max_context_chars": max_context_chars,
        "generation_budget_profile": generation_budget_profile,
        "max_output_tokens": max_output_tokens,
    }


def is_local_path_like(value: str) -> bool:
    expanded = Path(value).expanduser()
    return expanded.is_absolute() or value.startswith(".") or value.startswith("~")


def build_release_web_guidance(
    *,
    vectors: int,
    default_llm_provider: str,
    default_llm_model: str | None,
    default_llm_base_url: str | None,
    query_timeout_seconds: int,
    embedding_model: str,
) -> dict[str, object]:
    steps = [
        "기본 시작 경로는 `run_doc_rag.bat` 하나로 유지합니다.",
    ]
    status = "ready"
    headline = "기본 웹 MVP 경로로 바로 사용할 수 있습니다."
    runtime_profile = build_runtime_profile(
        provider=default_llm_provider,
        model=default_llm_model,
        timeout_seconds=query_timeout_seconds,
    )

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

    if runtime_profile["status"] == RUNTIME_PROFILE_EXPERIMENTAL:
        status = "runtime_warning"
        headline = "현재 런타임 프로파일은 연결 가능하지만 운영 기본값으로는 아직 미검증입니다."
        steps.append(str(runtime_profile["recommendation"]))
    elif runtime_profile["status"] == RUNTIME_PROFILE_NOT_RECOMMENDED:
        status = "needs_verified_runtime"
        headline = "현재 런타임 프로파일은 기본 운영 경로로 비권장입니다."
        steps.append(str(runtime_profile["recommendation"]))
    else:
        steps.append(str(runtime_profile["recommendation"]))

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
        "runtime_profile": runtime_profile,
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
