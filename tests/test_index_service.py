from __future__ import annotations

import json
import time
from pathlib import Path

from langchain_core.documents import Document

from services import index_service


def test_expand_reindex_collection_keys_for_default_uses_core_runtime_only():
    keys = index_service.expand_reindex_collection_keys("all")

    assert keys == ["all"]


def test_expand_reindex_collection_keys_can_include_compatibility_bundle():
    keys = index_service.expand_reindex_collection_keys("all", include_compatibility_bundle=True)

    assert keys[0] == "all"
    assert "fr" in keys
    assert "ge" in keys
    assert "uk" in keys


def test_expand_reindex_collection_keys_for_named_collection_includes_default():
    keys = index_service.expand_reindex_collection_keys("uk")

    assert keys == ["uk", "all"]


def test_reindex_with_related_returns_nested_results(monkeypatch):
    monkeypatch.setattr(
        index_service,
        "expand_reindex_collection_keys",
        lambda collection_key="all", include_compatibility_bundle=False: ["uk", "all"],
    )
    monkeypatch.setattr(
        index_service,
        "reindex_single_collection",
        lambda reset=True, collection_key="all": {
            "collection_key": collection_key,
            "collection": f"mock_{collection_key}",
            "docs": 1,
            "docs_total": 1,
            "chunks": 2,
            "vectors": 3,
            "persist_dir": "mock",
            "cap": {},
            "chunking": {"mode": "char"},
            "validation": {"summary_text": "ok"},
        },
    )

    result = index_service.reindex_with_related(reset=True, collection_key="uk")

    assert result["collection_key"] == "uk"
    assert result["reindex_scope"] == "selected_plus_default"
    assert result["related_collection_keys"] == ["uk", "all"]
    assert result["collections"]["uk"]["vectors"] == 3
    assert result["collections"]["all"]["vectors"] == 3


def test_reindex_with_related_marks_default_plus_compatibility_bundle(monkeypatch):
    monkeypatch.setattr(
        index_service,
        "expand_reindex_collection_keys",
        lambda collection_key="all", include_compatibility_bundle=False: ["all", "eu", "fr"],
    )
    monkeypatch.setattr(
        index_service,
        "reindex_single_collection",
        lambda reset=True, collection_key="all": {
            "collection_key": collection_key,
            "collection": f"mock_{collection_key}",
            "docs": 1,
            "docs_total": 1,
            "chunks": 2,
            "vectors": 3,
            "persist_dir": "mock",
            "cap": {},
            "chunking": {"mode": "char"},
            "validation": {"summary_text": "ok"},
        },
    )

    result = index_service.reindex_with_related(
        reset=True,
        collection_key="all",
        include_compatibility_bundle=True,
    )

    assert result["reindex_scope"] == "default_plus_compatibility_bundle"
    assert result["compatibility_bundle"]["included"] is True


def test_build_collection_source_records_uses_manifest_seed_metadata(monkeypatch):
    monkeypatch.setattr(index_service, "_load_managed_source_records", lambda collection_key="all": [])

    records = index_service.build_collection_source_records("fr")

    assert len(records) == 1
    record = records[0]
    assert record["collection_key"] == "fr"
    assert record["metadata"]["dataset"] == "sample-eu-science-history"
    assert record["metadata"]["source_type"] == "seed_markdown"
    assert record["metadata"]["country"] == "france"
    assert record["metadata"]["doc_type"] == "country"
    assert record["metadata"]["tags"] == ["sample-pack", "country:france"]


def test_prepare_vectorstore_documents_serializes_complex_metadata():
    docs = [
        Document(
            page_content="sample",
            metadata={
                "source": "all.md",
                "tags": ["sample-pack", "summary"],
                "nested": {"dataset": "sample"},
                "rank": 1,
                "empty": None,
            },
        )
    ]

    prepared = index_service._prepare_vectorstore_documents(docs)

    assert prepared[0].page_content == "sample"
    assert prepared[0].metadata == {
        "source": "all.md",
        "tags": '["sample-pack", "summary"]',
        "nested": '{"dataset": "sample"}',
        "rank": 1,
    }
    assert docs[0].metadata["tags"] == ["sample-pack", "summary"]


def test_record_collection_embedding_fingerprint_persists_manifest(monkeypatch, tmp_path: Path):
    monkeypatch.setattr(index_service, "PERSIST_DIR", str(tmp_path))
    monkeypatch.setattr(index_service.runtime_service, "get_embedding_model", lambda: "BAAI/bge-m3")
    monkeypatch.setattr(index_service.runtime_service, "utc_now_iso", lambda: "2026-03-25T00:00:00+00:00")

    record = index_service.record_collection_embedding_fingerprint("all", vector_count=37)

    manifest = json.loads((tmp_path / "embedding_fingerprints.json").read_text(encoding="utf-8"))
    assert record["collection_key"] == "all"
    assert manifest["items"]["all"]["vector_count"] == 37
    assert manifest["items"]["all"]["embedding_fingerprint"] == record["embedding_fingerprint"]


def test_get_embedding_fingerprint_status_reports_mismatch(monkeypatch):
    monkeypatch.setattr(index_service, "get_vector_count_snapshot", lambda collection_key="all", max_age_seconds=5.0: 1)
    monkeypatch.setattr(
        index_service,
        "get_collection_embedding_record",
        lambda key: {"embedding_fingerprint": "old", "embedding_model": "old-model"},
    )
    monkeypatch.setattr(index_service.runtime_service, "get_embedding_model", lambda: "BAAI/bge-m3")

    status = index_service.get_embedding_fingerprint_status(["all"])

    assert status["status"] == "mismatch"
    assert status["mismatch_keys"] == ["all"]


def test_get_vector_count_snapshot_uses_ttl_cache(monkeypatch):
    collection_name = index_service.collection_service.get_collection_name("all")
    calls: list[str] = []
    monkeypatch.setattr(
        index_service,
        "get_vector_count_fast",
        lambda name: calls.append(name) or 7,
    )
    index_service.invalidate_runtime_state()

    first = index_service.get_vector_count_snapshot("all", max_age_seconds=10.0)
    second = index_service.get_vector_count_snapshot("all", max_age_seconds=10.0)

    assert first == 7
    assert second == 7
    assert calls == [collection_name]


def test_invalidate_runtime_state_clears_vector_count_snapshot(monkeypatch):
    collection_name = index_service.collection_service.get_collection_name("all")
    values = iter([5, 9])
    monkeypatch.setattr(index_service, "get_vector_count_fast", lambda name: next(values))
    index_service.invalidate_runtime_state()

    cached = index_service.get_vector_count_snapshot("all", max_age_seconds=10.0)
    index_service.invalidate_runtime_state(["all"])
    refreshed = index_service.get_vector_count_snapshot("all", max_age_seconds=10.0)

    assert cached == 5
    assert refreshed == 9
