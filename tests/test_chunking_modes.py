from __future__ import annotations

from langchain_core.documents import Document
import pytest

import app_api
from common import CHUNKING_MODE_CHAR, CHUNKING_MODE_TOKEN, normalize_chunking_mode, split_by_markdown_headers


def _sample_docs() -> list[Document]:
    text = (
        "## 프랑스 과학사\n"
        "프랑스 과학사에 대한 설명 문장입니다. " * 40
        + "\n### 근대 과학\n근대 과학에 대한 보조 설명입니다. " * 20
    )
    return [
        Document(
            page_content=text,
            metadata={
                "source": "sample.md",
                "country": "all",
                "doc_type": "summary",
            },
        )
    ]


def test_split_by_markdown_headers_supports_char_and_token_mode():
    docs = _sample_docs()

    char_chunks = split_by_markdown_headers(
        docs,
        chunk_size=200,
        chunk_overlap=30,
        chunking_mode=CHUNKING_MODE_CHAR,
    )
    token_chunks = split_by_markdown_headers(
        docs,
        chunk_size=120,
        chunk_overlap=20,
        chunking_mode=CHUNKING_MODE_TOKEN,
    )

    assert len(char_chunks) > 0
    assert len(token_chunks) > 0
    assert all(chunk.metadata["source"] == "sample.md" for chunk in char_chunks)
    assert all(chunk.metadata["source"] == "sample.md" for chunk in token_chunks)
    assert any("h2" in chunk.metadata for chunk in char_chunks)
    assert any("h2" in chunk.metadata for chunk in token_chunks)


def test_normalize_chunking_mode_rejects_invalid_value():
    with pytest.raises(ValueError):
        normalize_chunking_mode("invalid-mode")


def test_get_chunking_config_fallbacks_to_char(monkeypatch):
    monkeypatch.setenv("DOC_RAG_CHUNKING_MODE", "token")
    monkeypatch.setenv("DOC_RAG_CHUNK_TOKEN_ENCODING", "cl100k_base")
    config = app_api.get_chunking_config()
    assert config["mode"] == CHUNKING_MODE_TOKEN
    assert config["token_encoding"] == "cl100k_base"

    monkeypatch.setenv("DOC_RAG_CHUNKING_MODE", "not-valid")
    fallback = app_api.get_chunking_config()
    assert fallback["mode"] == CHUNKING_MODE_CHAR
