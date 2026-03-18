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
