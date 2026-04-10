from __future__ import annotations

from services import tool_registry_service


def test_tool_registry_exposes_v1_5_wp1_candidates():
    names = tool_registry_service.list_tool_names()

    assert names == [
        "search_docs",
        "read_doc",
        "list_collections",
        "health_check",
        "reindex",
        "list_upload_requests",
        "approve_upload_request",
        "reject_upload_request",
    ]

    search_definition = tool_registry_service.get_tool_definition("search_docs")
    assert search_definition["category"] == "retrieval"
    assert search_definition["side_effect"] == "read"
    assert search_definition["input_schema"]["required"] == ["query"]

    reindex_definition = tool_registry_service.get_tool_definition("reindex")
    assert reindex_definition["side_effect"] == "write"


def test_read_doc_tool_reads_seed_markdown_without_mutation():
    result = tool_registry_service.invoke_tool(
        "read_doc",
        {"collection": "fr", "doc_key": "fr"},
    )

    assert result["ok"] is True
    assert result["result"]["origin"] == "seed"
    assert result["result"]["collection_key"] == "fr"
    assert result["result"]["metadata"]["country"] == "france"
    assert "에콜 폴리테크니크" in result["result"]["content"]


def test_search_docs_tool_uses_generic_core_route_by_default(monkeypatch):
    def fake_build_collection_context(*, question, collection_keys, trace, budget):
        trace.update(
            {
                "collections": list(collection_keys),
                "sources": [
                    {
                        "source": "fr.md",
                        "h2": "에콜 폴리테크니크",
                        "collection_key": collection_keys[0],
                    }
                ],
            }
        )
        return f"context for {question}"

    monkeypatch.setattr(
        tool_registry_service.query_service,
        "build_collection_context",
        fake_build_collection_context,
    )

    result = tool_registry_service.invoke_tool(
        "search_docs",
        {"query": "프랑스 과학 인재 양성을 요약해줘."},
    )

    assert result["ok"] is True
    assert result["result"]["query_profile"] == "generic"
    assert result["result"]["collections"] == ["all"]
    assert result["result"]["route_reason"] == "default"
    assert result["result"]["sources"][0]["collection_key"] == "all"


def test_search_docs_tool_can_opt_into_sample_pack_keyword_route(monkeypatch):
    def fake_build_collection_context(*, question, collection_keys, trace, budget):
        trace.update({"collections": list(collection_keys), "sources": []})
        return "sample-pack context"

    monkeypatch.setattr(
        tool_registry_service.query_service,
        "build_collection_context",
        fake_build_collection_context,
    )

    result = tool_registry_service.invoke_tool(
        "search_docs",
        {
            "query": "프랑스 과학 인재 양성을 요약해줘.",
            "query_profile": "sample_pack",
        },
    )

    assert result["ok"] is True
    assert result["result"]["query_profile"] == "sample_pack"
    assert result["result"]["collections"] == ["fr"]
    assert result["result"]["route_reason"] == "compatibility_keyword"


def test_write_tools_require_mutation_context():
    result = tool_registry_service.invoke_tool("reindex", {"collection": "all"})

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_NOT_ALLOWED"
