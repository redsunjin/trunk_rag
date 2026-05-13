from __future__ import annotations

from langchain_core.documents import Document

from scripts.validate_rag_doc import validate_markdown_text
from services import index_service


def test_normalize_documents_for_index_supports_source_file_alias(monkeypatch):
    monkeypatch.setattr(index_service.runtime_service, "is_extended_metadata_enabled", lambda: True)
    docs = [
        Document(
            page_content="## 타임라인\n충분한 길이의 본문 설명입니다. " * 20,
            metadata={
                "source_file": "legacy_timeline.md",
                "country": "all",
                "doc_type": "summary",
                "year_text": "1727",
                "scientist": "아이작 뉴턴",
            },
        )
    ]

    normalized = index_service.normalize_documents_for_index(docs, collection_key="all")
    metadata = normalized[0].metadata
    assert metadata["source"] == "legacy_timeline.md"
    assert metadata["source_file"] == "legacy_timeline.md"
    assert metadata["country"] == "all"
    assert metadata["doc_type"] == "summary"
    assert metadata["topic"] == "europe_science_history"
    assert metadata["year_text"] == "1727"
    assert metadata["scientist"] == "아이작 뉴턴"


def test_normalize_documents_for_index_keeps_required_fields_when_extension_disabled(monkeypatch):
    monkeypatch.setattr(index_service.runtime_service, "is_extended_metadata_enabled", lambda: False)
    docs = [
        Document(
            page_content="## 본문\n테스트 설명입니다. " * 20,
            metadata={"source": "legacy.md", "country": "france", "doc_type": "country"},
        )
    ]

    normalized = index_service.normalize_documents_for_index(docs, collection_key="fr")
    metadata = normalized[0].metadata
    assert metadata["source"] == "legacy.md"
    assert metadata["country"] == "france"
    assert metadata["doc_type"] == "country"
    assert "source_file" not in metadata
    assert "topic" not in metadata


def test_validate_markdown_text_allows_source_file_compat():
    report = validate_markdown_text(
        source="legacy_timeline.md",
        text="## 테스트\n타임라인 본문입니다. " * 20,
        metadata={
            "source_file": "legacy_timeline.md",
            "country": "all",
            "doc_type": "summary",
        },
    )
    assert report["usable"] is True
    assert report["reasons"] == []
