from __future__ import annotations

from services import graph_lite_service, graph_lite_snapshot_builder


def test_build_graph_lite_snapshot_adds_contract_metadata(monkeypatch):
    def _fake_build_graph_snapshot(collection_key: str = "all"):
        return {
            "nodes": [{"id": "newton", "label": "Newton", "sources": ["uk.md"], "collections": ["uk"]}],
            "edges": [],
            "stats": {"collection_key": collection_key, "source_docs": 1, "section_hits": 1},
        }

    monkeypatch.setattr(
        graph_lite_snapshot_builder.graphrag_poc_service,
        "build_graph_snapshot",
        _fake_build_graph_snapshot,
    )

    snapshot = graph_lite_snapshot_builder.build_graph_lite_snapshot(collection_key="uk")

    assert snapshot["stats"]["contract_version"] == graph_lite_service.GRAPH_LITE_CONTRACT_VERSION
    assert snapshot["stats"]["builder"] == "graph_lite_snapshot_builder.v1"
    assert snapshot["stats"]["collection_key"] == "uk"
    assert snapshot["nodes"][0]["id"] == "newton"


def test_build_and_export_graph_lite_snapshot_writes_loadable_snapshot(tmp_path, monkeypatch):
    def _fake_build_graph_snapshot(collection_key: str = "all"):
        return {
            "nodes": [
                {
                    "id": "newton",
                    "label": "Newton",
                    "sources": ["uk.md"],
                    "collections": ["uk"],
                },
                {
                    "id": "voltaire",
                    "label": "Voltaire",
                    "sources": ["uk.md"],
                    "collections": ["uk"],
                },
            ],
            "edges": [
                {
                    "source": "newton",
                    "target": "voltaire",
                    "weight": 2,
                    "collections": ["uk"],
                    "evidence": [
                        {
                            "source": "uk.md",
                            "heading": "뉴턴과 볼테르",
                            "excerpt": "뉴턴의 국장은 볼테르에게 충격을 주었다.",
                        }
                    ],
                }
            ],
            "stats": {"collection_key": collection_key, "source_docs": 1, "section_hits": 1},
        }

    monkeypatch.setattr(
        graph_lite_snapshot_builder.graphrag_poc_service,
        "build_graph_snapshot",
        _fake_build_graph_snapshot,
    )

    payload = graph_lite_snapshot_builder.build_and_export_graph_lite_snapshot(
        collection_key="uk",
        output_dir=tmp_path,
    )
    summary_paths = graph_lite_snapshot_builder.write_build_summary(payload, output_dir=tmp_path)

    snapshot = graph_lite_service.load_relation_snapshot(tmp_path)
    result = graph_lite_service.query_relation_snapshot(snapshot, "뉴턴과 볼테르의 관계를 설명해줘.")

    assert payload["entity_count"] == 2
    assert payload["relation_count"] == 1
    assert result["status"] == "hit"
    assert (tmp_path / "entities.jsonl").exists()
    assert (tmp_path / "relations.jsonl").exists()
    assert (tmp_path / "ingest_stats.json").exists()
    assert "summary_json" in summary_paths
    assert "summary_report" in summary_paths
