from __future__ import annotations

import pytest

from common import default_llm_model, resolve_llm_config


def test_default_llm_model_supports_groq():
    assert default_llm_model("groq") == "groq-model"


def test_resolve_llm_config_reads_groq_env(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "groq-test-key")
    monkeypatch.setenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    monkeypatch.delenv("LLM_MODEL", raising=False)

    resolved = resolve_llm_config(provider="groq")

    assert resolved == (
        "groq",
        "groq-model",
        "groq-test-key",
        "https://api.groq.com/openai/v1",
    )


def test_resolve_llm_config_requires_supported_provider():
    with pytest.raises(ValueError):
        resolve_llm_config(provider="not-supported")
