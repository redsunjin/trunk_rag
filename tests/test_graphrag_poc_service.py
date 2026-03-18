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


def test_filter_graph_snapshot_and_answer_graph_snapshot():
    snapshot = {
        "nodes": [
            {"id": "newton", "label": "Newton", "sources": ["uk.md"], "collections": ["uk"]},
            {"id": "voltaire", "label": "Voltaire", "sources": ["fr.md"], "collections": ["fr"]},
            {"id": "helmholtz", "label": "Helmholtz", "sources": ["ge.md"], "collections": ["ge"]},
        ],
        "edges": [
            {
                "source": "newton",
                "target": "voltaire",
                "weight": 2,
                "collections": ["uk", "fr"],
                "evidence": [{"source": "eu_summry.md", "heading": "2. 계몽주의 시대"}],
            },
            {
                "source": "helmholtz",
                "target": "voltaire",
                "weight": 1,
                "collections": ["ge"],
                "evidence": [{"source": "ge.md", "heading": "5. 독일 물리학회"}],
            },
        ],
        "stats": {"source_docs": 3, "section_hits": 2, "nodes": 3, "edges": 2},
    }

    filtered = graphrag_poc_service.filter_graph_snapshot(snapshot, ["uk", "fr"])
    assert filtered["stats"]["filtered"] is True
    assert len(filtered["edges"]) == 1

    answer = graphrag_poc_service.answer_graph_snapshot(
        filtered,
        "뉴턴과 볼테르의 관계를 설명해줘.",
        max_hops=2,
    )
    assert "질문 재진술" in answer["answer"]
    assert "뉴턴" in answer["answer"]
    assert "볼테르" in answer["answer"]
