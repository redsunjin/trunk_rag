from __future__ import annotations

from services import index_service


def test_expand_reindex_collection_keys_for_default_includes_route_collections():
    keys = index_service.expand_reindex_collection_keys("all")

    assert keys[0] == "all"
    assert "fr" in keys
    assert "ge" in keys
    assert "uk" in keys


def test_expand_reindex_collection_keys_for_named_collection_includes_default():
    keys = index_service.expand_reindex_collection_keys("uk")

    assert keys == ["uk", "all"]


def test_reindex_with_related_returns_nested_results(monkeypatch):
    monkeypatch.setattr(index_service, "expand_reindex_collection_keys", lambda collection_key="all": ["uk", "all"])
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
