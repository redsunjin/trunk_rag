from __future__ import annotations

from core.collection_manifest import build_seed_document_metadata, get_seed_document_collection_key
from core import settings
from services import collection_service


def test_collection_manifest_defaults_are_loaded():
    assert settings.DEFAULT_COLLECTION_KEY == "all"
    assert settings.COLLECTION_NAME == "w2_007_header_rag"
    assert settings.COLLECTION_CONFIGS["fr"]["name"] == "rag_science_history_fr"
    assert settings.DEFAULT_RUNTIME_COLLECTION_KEYS == ["all"]
    assert settings.COMPATIBILITY_BUNDLE_CONFIG["key"] == "sample_pack"
    assert settings.SEED_CORPUS_CONFIG["role"] == "demo_bootstrap"
    assert settings.SEED_CORPUS_CONFIG["dataset"] == "sample-eu-science-history"


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


def test_compatibility_bundle_keys_come_from_manifest():
    assert collection_service.list_default_runtime_collection_keys() == ["all"]
    assert collection_service.list_compatibility_collection_keys() == ["eu", "fr", "ge", "it", "uk"]
    assert "project_docs" not in collection_service.list_default_runtime_collection_keys()
    assert "project_docs" not in collection_service.list_compatibility_collection_keys()


def test_project_docs_collection_is_explicit_only():
    config = collection_service.get_collection_config("project_docs")

    assert config["name"] == "rag_project_docs"
    assert config["seed_doc_keys"] == []
    assert config["keywords"] == []
    assert collection_service.resolve_collection_key("project_docs") == "project_docs"


def test_seed_corpus_config_describes_demo_bootstrap_boundary():
    corpus = collection_service.get_seed_corpus_config()

    assert corpus["key"] == "sample_pack_bootstrap"
    assert corpus["role"] == "demo_bootstrap"
    assert corpus["dataset"] == "sample-eu-science-history"
    assert "demo corpus" in corpus["description"]
    assert "not product-domain data" in corpus["description"]


def test_resolve_collection_keys_for_query_defaults_to_all_without_keyword_routing():
    keys, route_reason, allow_default_fallback = collection_service.resolve_collection_keys_for_query(
        "프랑스와 독일의 과학 제도화를 비교해줘.",
        None,
        None,
        allow_keyword_routing=False,
    )

    assert keys == ["all"]
    assert route_reason == "default"
    assert allow_default_fallback is False


def test_resolve_collection_keys_for_query_allows_sample_pack_keyword_multi_when_enabled():
    keys, route_reason, allow_default_fallback = collection_service.resolve_collection_keys_for_query(
        "프랑스와 독일의 과학 제도화를 비교해줘.",
        None,
        None,
        allow_keyword_routing=True,
    )

    assert keys == ["fr", "ge"]
    assert route_reason == "compatibility_keyword_multi"
    assert allow_default_fallback is True
