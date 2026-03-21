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


def test_build_release_web_guidance_marks_reindex_when_vectors_empty():
    guidance = runtime_service.build_release_web_guidance(
        vectors=0,
        default_llm_provider="ollama",
        default_llm_model="qwen3:4b",
        default_llm_base_url="http://localhost:11434",
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
        default_llm_model="qwen3:4b",
        default_llm_base_url="http://localhost:11434",
        embedding_model="/models/local-bge-m3",
    )

    assert guidance["status"] == "ready"
    assert any("/app" in step for step in guidance["steps"])
    assert any("qwen3:4b" in step for step in guidance["steps"])


def test_get_default_llm_config_defaults_to_ollama(monkeypatch):
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)

    resolved = runtime_service.get_default_llm_config()

    assert resolved == {
        "provider": "ollama",
        "model": "qwen3:4b",
        "base_url": "http://localhost:11434",
    }
