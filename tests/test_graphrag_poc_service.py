from __future__ import annotations

from services import graphrag_poc_service


def test_detect_entity_ids_and_query_snapshot():
    snapshot = {
        "nodes": [
            {"id": "newton", "label": "Newton", "sources": ["uk.md"], "collections": ["uk"]},
            {"id": "voltaire", "label": "Voltaire", "sources": ["ge.md"], "collections": ["ge"]},
            {"id": "leibniz", "label": "Leibniz", "sources": ["ge.md"], "collections": ["ge"]},
        ],
        "edges": [
            {
                "source": "newton",
                "target": "voltaire",
                "weight": 1,
                "collections": ["ge"],
                "evidence": [{"source": "ge.md", "heading": "2. 계몽주의 시대"}],
            },
            {
                "source": "voltaire",
                "target": "leibniz",
                "weight": 1,
                "collections": ["ge"],
                "evidence": [{"source": "ge.md", "heading": "2. 계몽주의 시대"}],
            },
        ],
        "stats": {},
    }

    detected = graphrag_poc_service.detect_entity_ids("뉴턴과 볼테르의 연결을 설명해줘.")
    assert detected == ["newton", "voltaire"]

    result = graphrag_poc_service.query_graph_snapshot(
        snapshot,
        "뉴턴의 국장과 볼테르의 충격을 연결해줘.",
        max_hops=2,
    )
    assert "newton" in result["matched_entities"]
    assert "voltaire" in result["matched_entities"]
    assert result["relations"]
