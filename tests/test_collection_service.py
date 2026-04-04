from __future__ import annotations

from core.collection_manifest import build_seed_document_metadata, get_seed_document_collection_key
from core import settings
from services import collection_service


def test_collection_manifest_defaults_are_loaded():
    assert settings.DEFAULT_COLLECTION_KEY == "all"
    assert settings.COLLECTION_NAME == "w2_007_header_rag"
    assert settings.COLLECTION_CONFIGS["fr"]["name"] == "rag_science_history_fr"


def test_collection_defaults_come_from_manifest():
    assert collection_service.default_country_for_collection("all") == "all"
    assert collection_service.default_doc_type_for_collection("all") == "summary"
    assert collection_service.default_country_for_collection("ge") == "germany"
    assert collection_service.default_doc_type_for_collection("ge") == "country"


def test_seed_document_metadata_comes_from_manifest():
    metadata = build_seed_document_metadata("fr.md")

    assert get_seed_document_collection_key("fr.md") == "fr"
    assert metadata["dataset"] == "sample-eu-science-history"
    assert metadata["source_type"] == "seed_markdown"
    assert metadata["country"] == "france"
    assert metadata["doc_type"] == "country"
    assert metadata["tags"] == ["sample-pack", "country:france"]
