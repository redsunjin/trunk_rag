from __future__ import annotations

from services import runtime_service


def test_get_max_context_chars_defaults_to_safe_limit(monkeypatch):
    monkeypatch.delenv("DOC_RAG_MAX_CONTEXT_CHARS", raising=False)

    resolved = runtime_service.get_max_context_chars()

    assert resolved == 1500


def test_get_max_context_chars_invalid_value_falls_back(monkeypatch):
    monkeypatch.setenv("DOC_RAG_MAX_CONTEXT_CHARS", "bad-value")

    resolved = runtime_service.get_max_context_chars()

    assert resolved == 1500


def test_get_max_context_chars_blank_value_uses_default_without_warning(monkeypatch):
    monkeypatch.setenv("DOC_RAG_MAX_CONTEXT_CHARS", "")

    resolved = runtime_service.get_max_context_chars()

    assert resolved == 1500


def test_build_release_web_guidance_marks_reindex_when_vectors_empty():
    guidance = runtime_service.build_release_web_guidance(
        vectors=0,
        default_llm_provider="ollama",
        default_llm_model="llama3.1:8b",
        default_llm_base_url="http://localhost:11434",
        query_timeout_seconds=30,
        embedding_model="BAAI/bge-m3",
    )

    assert guidance["status"] == "needs_reindex"
    assert "인덱싱" in guidance["headline"]
    assert any("build_index.py --reset" in step for step in guidance["steps"])
    assert any("Ollama" in step for step in guidance["steps"])


def test_build_release_web_guidance_marks_ready_when_vectors_exist():
    guidance = runtime_service.build_release_web_guidance(
        vectors=7,
        default_llm_provider="ollama",
        default_llm_model="llama3.1:8b",
        default_llm_base_url="http://localhost:11434",
        query_timeout_seconds=30,
        embedding_model="/models/local-bge-m3",
    )

    assert guidance["status"] == "ready"
    assert any("/app" in step for step in guidance["steps"])
    assert any("llama3.1:8b" in step for step in guidance["steps"])
    assert guidance["runtime_profile"]["status"] == "verified"


def test_get_default_llm_config_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    resolved = runtime_service.get_default_llm_config()

    assert resolved == {
        "provider": "ollama",
        "model": "llama3.1:8b",
        "base_url": "http://localhost:11434",
    }


def test_build_release_web_guidance_supports_groq():
    guidance = runtime_service.build_release_web_guidance(
        vectors=7,
        default_llm_provider="groq",
        default_llm_model="llama-3.3-70b-versatile",
        default_llm_base_url="https://api.groq.com/openai/v1",
        query_timeout_seconds=30,
        embedding_model="/models/local-bge-m3",
    )

    assert guidance["status"] == "runtime_warning"
    assert any("GROQ_API_KEY" in step for step in guidance["steps"])


def test_build_runtime_profile_marks_verified_local_ollama():
    profile = runtime_service.build_runtime_profile(
        provider="ollama",
        model="llama3.1:8b",
        timeout_seconds=30,
    )

    assert profile["status"] == "verified"
    assert profile["scope"] == "local"


def test_build_runtime_profile_marks_low_timeout_as_experimental():
    profile = runtime_service.build_runtime_profile(
        provider="ollama",
        model="llama3.1:8b",
        timeout_seconds=15,
    )

    assert profile["status"] == "experimental"
    assert "30" in str(profile["recommendation"])


def test_build_runtime_profile_marks_qwen_as_not_recommended():
    profile = runtime_service.build_runtime_profile(
        provider="ollama",
        model="qwen3:4b",
        timeout_seconds=30,
    )

    assert profile["status"] == "not_recommended"
    assert "llama3.1:8b" in str(profile["recommendation"])


def test_plan_query_budget_keeps_verified_local_single_budget():
    budget = runtime_service.plan_query_budget(
        provider="ollama",
        model="llama3.1:8b",
        timeout_seconds=30,
        collection_count=1,
        route_reason="default",
    )

    assert budget["profile"] == "verified_local_single"
    assert budget["per_collection_k"] == 3
    assert budget["per_collection_fetch_k"] == 10
    assert budget["max_total_docs"] == 3
    assert budget["generation_budget_profile"] == "standard"


def test_plan_query_budget_reduces_verified_local_multi_budget():
    budget = runtime_service.plan_query_budget(
        provider="ollama",
        model="llama3.1:8b",
        timeout_seconds=30,
        collection_count=2,
        route_reason="keyword_multi",
    )

    assert budget["profile"] == "verified_local_multi"
    assert budget["per_collection_k"] == 2
    assert budget["per_collection_fetch_k"] == 4
    assert budget["max_total_docs"] == 4
    assert budget["generation_budget_profile"] == "compact"


def test_plan_query_budget_restricts_not_recommended_local_runtime():
    budget = runtime_service.plan_query_budget(
        provider="ollama",
        model="qwen3:4b",
        timeout_seconds=30,
        collection_count=1,
        route_reason="default",
    )

    assert budget["profile"] == "not_recommended_local"
    assert budget["per_collection_k"] == 1
    assert budget["max_total_docs"] == 1
    assert budget["generation_budget_profile"] == "restricted"
