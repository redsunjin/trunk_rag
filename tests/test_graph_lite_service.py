from __future__ import annotations

import json
from pathlib import Path

from services import graph_lite_service


def _write_jsonl(path: Path, records: list[dict[str, object]]) -> None:
    path.write_text("\n".join(json.dumps(item, ensure_ascii=False) for item in records) + "\n", encoding="utf-8")


def _write_snapshot(tmp_path: Path) -> Path:
    _write_jsonl(
        tmp_path / "entities.jsonl",
        [
            {
                "id": "newton",
                "label": "Newton",
                "aliases": ["뉴턴"],
                "sources": ["uk.md"],
                "collections": ["uk"],
            },
            {
                "id": "voltaire",
                "label": "Voltaire",
                "aliases": ["볼테르"],
                "sources": ["fr.md"],
                "collections": ["fr"],
            },
            {
                "id": "enlightenment",
                "label": "Enlightenment",
                "aliases": ["계몽주의"],
                "sources": ["ge.md"],
                "collections": ["ge"],
            },
            {
                "id": "humboldt_university",
                "label": "Humboldt University",
                "aliases": ["훔볼트 대학"],
                "sources": ["ge.md"],
                "collections": ["ge"],
            },
        ],
    )
    _write_jsonl(
        tmp_path / "relations.jsonl",
        [
            {
                "source": "newton",
                "target": "voltaire",
                "predicate": "influenced",
                "weight": 3,
                "collections": ["uk", "fr"],
                "evidence": [
                    {
                        "source": "uk.md",
                        "heading": "2. 뉴턴의 사회적 권위",
                        "excerpt": "뉴턴의 국장은 볼테르에게 강한 인상을 주었고 계몽주의 확산의 상징이 됐다.",
                    }
                ],
            },
            {
                "source": "voltaire",
                "target": "enlightenment",
                "predicate": "diffused",
                "weight": 2,
                "collections": ["fr", "ge"],
                "evidence": [
                    {
                        "source": "fr.md",
                        "heading": "3. 계몽주의 확산",
                        "excerpt": "볼테르의 해석은 프랑스와 독일의 계몽주의 확산과 연결된다.",
                    }
                ],
            },
            {
                "source": "humboldt_university",
                "target": "enlightenment",
                "predicate": "institutionalized",
                "weight": 1,
                "collections": ["ge"],
                "evidence": [
                    {
                        "source": "ge.md",
                        "heading": "4. 훔볼트 모델",
                        "excerpt": "훔볼트 대학은 연구와 교육의 통합을 제도화했다.",
                    }
                ],
            },
        ],
    )
    (tmp_path / "ingest_stats.json").write_text(
        json.dumps({"collection_key": "all", "source_docs": 3}, ensure_ascii=False),
        encoding="utf-8",
    )
    return tmp_path


def test_load_relation_snapshot_normalizes_entities_relations_and_stats(tmp_path):
    snapshot_dir = _write_snapshot(tmp_path)

    snapshot = graph_lite_service.load_relation_snapshot(snapshot_dir)

    assert snapshot.stats["contract_version"] == graph_lite_service.GRAPH_LITE_CONTRACT_VERSION
    assert snapshot.stats["nodes"] == 4
    assert snapshot.stats["edges"] == 3
    assert snapshot.entities["newton"].aliases
    assert snapshot.relations[0].predicate == "influenced"


def test_detect_relation_query_intent_requires_multi_entity_and_relation_keyword(tmp_path):
    snapshot = graph_lite_service.load_relation_snapshot(_write_snapshot(tmp_path))

    intent = graph_lite_service.detect_relation_query_intent(
        snapshot,
        "뉴턴과 볼테르의 관계가 계몽주의 확산으로 어떻게 이어졌는지 설명해줘.",
    )

    assert intent["relation_heavy"] is True
    assert intent["reason"] == "keyword_and_multi_entity"
    assert intent["entity_ids"] == ["enlightenment", "newton", "voltaire"]
    assert "관계" in intent["keyword_hits"]


def test_query_relation_snapshot_returns_ranked_relations_and_context(tmp_path):
    snapshot = graph_lite_service.load_relation_snapshot(_write_snapshot(tmp_path))

    result = graph_lite_service.query_relation_snapshot(
        snapshot,
        "뉴턴과 볼테르의 관계가 계몽주의 확산으로 어떻게 이어졌는지 설명해줘.",
        collection_keys=["uk", "fr", "ge"],
        max_hops=2,
    )

    assert result["status"] == "hit"
    assert result["fallback_used"] is False
    assert result["relations"]
    assert result["relations"][0]["source"] == "newton"
    assert result["relations"][0]["target"] == "voltaire"
    assert "graph-lite:1" in result["context"]
    assert "뉴턴의 국장" in result["context"]


def test_query_relation_snapshot_falls_back_for_non_relation_heavy_question(tmp_path):
    snapshot = graph_lite_service.load_relation_snapshot(_write_snapshot(tmp_path))

    result = graph_lite_service.query_relation_snapshot(snapshot, "뉴턴을 요약해줘.")

    assert result["status"] == "fallback"
    assert result["fallback_used"] is True
    assert result["fallback_reason"] == "single_query_entity"
    assert result["relations"] == []
    assert result["context"] == ""


def test_query_relation_snapshot_falls_back_when_collection_filter_has_no_hit(tmp_path):
    snapshot = graph_lite_service.load_relation_snapshot(_write_snapshot(tmp_path))

    result = graph_lite_service.query_relation_snapshot(
        snapshot,
        "뉴턴과 볼테르의 관계를 설명해줘.",
        collection_keys=["it"],
        max_hops=2,
    )

    assert result["status"] == "fallback"
    assert result["fallback_reason"] == "no_graph_hit"
    assert result["relations"] == []


def test_append_graph_lite_context_is_noop_for_fallback(tmp_path):
    snapshot = graph_lite_service.load_relation_snapshot(_write_snapshot(tmp_path))
    result = graph_lite_service.query_relation_snapshot(snapshot, "뉴턴을 요약해줘.")

    context = graph_lite_service.append_graph_lite_context("base context", result)

    assert context == "base context"


def test_load_default_relation_snapshot_uses_env_override(tmp_path, monkeypatch):
    snapshot_dir = _write_snapshot(tmp_path)
    monkeypatch.setenv(graph_lite_service.GRAPH_LITE_SNAPSHOT_DIR_ENV_KEY, str(snapshot_dir))

    snapshot = graph_lite_service.load_default_relation_snapshot()

    assert snapshot.source_dir == str(snapshot_dir)
    assert snapshot.stats["nodes"] == 4
