from __future__ import annotations

import json
import re
import time
from itertools import combinations
from pathlib import Path

from core.settings import DEFAULT_COLLECTION_KEY
from services import index_service

SECTION_HEADING_PATTERN = re.compile(r"^(?:##+|\d+\.)\s+")
KOREAN_TEXT_PATTERN = re.compile(r"[가-힣]")

ENTITY_SPECS: list[dict[str, object]] = [
    {"id": "newton", "label": "Newton", "aliases": ["뉴턴", "newton"]},
    {"id": "voltaire", "label": "Voltaire", "aliases": ["볼테르", "voltaire"]},
    {"id": "leibniz", "label": "Leibniz", "aliases": ["라이프니츠", "leibniz"]},
    {"id": "galileo", "label": "Galileo", "aliases": ["갈릴레오", "galileo"]},
    {"id": "medici", "label": "Medici", "aliases": ["메디치", "medici"]},
    {
        "id": "ecole_polytechnique",
        "label": "Ecole Polytechnique",
        "aliases": ["에콜 폴리테크니크", "ecole polytechnique", "école polytechnique"],
    },
    {
        "id": "humboldt_university",
        "label": "Humboldt University",
        "aliases": ["훔볼트 대학", "베를린 대학", "humboldt university"],
    },
    {
        "id": "royal_society",
        "label": "Royal Society",
        "aliases": ["왕립학회", "royal society"],
    },
    {
        "id": "padua_university",
        "label": "Padua University",
        "aliases": ["파도바 대학", "padua university"],
    },
    {
        "id": "bologna_university",
        "label": "Bologna University",
        "aliases": ["볼로냐", "볼로냐 대학", "bologna"],
    },
    {
        "id": "magnus_lab",
        "label": "Magnus Laboratory",
        "aliases": ["마그누스 실험실", "구스타프 마그누스", "gustav magnus", "magnus"],
    },
    {"id": "helmholtz", "label": "Helmholtz", "aliases": ["헬름홀츠", "helmholtz"]},
    {"id": "siemens", "label": "Siemens", "aliases": ["지멘스", "siemens"]},
    {
        "id": "german_physical_society",
        "label": "German Physical Society",
        "aliases": ["독일 물리학회", "dpg", "german physical society"],
    },
    {
        "id": "max_planck_institute",
        "label": "Max Planck Institute",
        "aliases": ["막스 플랑크 연구소", "max planck institute"],
    },
    {"id": "gottingen", "label": "Gottingen", "aliases": ["괴팅겐", "göttingen", "gottingen"]},
    {
        "id": "french_revolution",
        "label": "French Revolution",
        "aliases": ["프랑스 혁명", "french revolution"],
    },
    {
        "id": "napoleonic_wars",
        "label": "Napoleonic Wars",
        "aliases": ["나폴레옹 전쟁", "napoleonic wars"],
    },
    {
        "id": "great_fire_london",
        "label": "Great Fire of London",
        "aliases": ["런던 대화재", "great fire of london"],
    },
    {
        "id": "enlightenment",
        "label": "Enlightenment",
        "aliases": ["계몽주의", "enlightenment"],
    },
]

ENTITY_BY_ID = {str(item["id"]): item for item in ENTITY_SPECS}

GRAPH_CANDIDATE_SPECS: list[dict[str, object]] = [
    {
        "id": "GQ-09",
        "question": "뉴턴의 국장, 볼테르의 충격, 프랑스/독일 계몽주의 확산이 어떤 연쇄로 이어졌는지 설명해줘.",
        "expected_entities": ["newton", "voltaire", "enlightenment", "leibniz"],
    },
    {
        "id": "GQ-10",
        "question": "뉴턴과 라이프니츠의 미적분 논쟁이 양국 과학 자존심 경쟁으로 어떻게 번졌는지 설명해줘.",
        "expected_entities": ["newton", "leibniz", "voltaire"],
    },
    {
        "id": "GQ-12",
        "question": "마그누스 실험실에서 시작된 네트워크가 헬름홀츠, 지멘스, 독일 물리학회, 산업화로 어떻게 이어졌는지 설명해줘.",
        "expected_entities": ["magnus_lab", "helmholtz", "siemens", "german_physical_society"],
    },
    {
        "id": "GQ-14",
        "question": "프랑스 혁명, 나폴레옹 전쟁 이후 독일 재건, 런던 대화재가 각국 과학 제도 설계에 어떤 영향을 줬는지 연결해줘.",
        "expected_entities": ["french_revolution", "napoleonic_wars", "great_fire_london", "humboldt_university"],
    },
    {
        "id": "GQ-15",
        "question": "에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학을 한 관계망으로 놓고 각자의 역할을 설명해줘.",
        "expected_entities": [
            "ecole_polytechnique",
            "humboldt_university",
            "royal_society",
            "padua_university",
        ],
    },
    {
        "id": "GQ-16",
        "question": "괴팅겐의 과학 자산이 전쟁 중 보호되고 전후 인재 이동과 막스 플랑크 연구소 재건으로 이어진 흐름을 설명해줘.",
        "expected_entities": ["gottingen", "max_planck_institute", "helmholtz"],
    },
]


def _normalize_text(value: str) -> str:
    return value.lower()


def _entity_display_name(entity_id: str) -> str:
    spec = ENTITY_BY_ID.get(entity_id, {})
    aliases = spec.get("aliases", [])
    if isinstance(aliases, list):
        for alias in aliases:
            alias_text = str(alias).strip()
            if alias_text and KOREAN_TEXT_PATTERN.search(alias_text):
                return alias_text
    return str(spec.get("label", entity_id))


def split_markdown_sections(text: str, *, source_name: str) -> list[dict[str, str]]:
    sections: list[dict[str, str]] = []
    current_heading = source_name
    current_lines: list[str] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or set(line) == {"-"}:
            continue

        if SECTION_HEADING_PATTERN.match(line):
            if current_lines:
                body = "\n".join(current_lines).strip()
                if body:
                    sections.append({"heading": current_heading, "content": body})
            current_heading = line
            current_lines = []
            continue

        current_lines.append(raw_line)

    if current_lines:
        body = "\n".join(current_lines).strip()
        if body:
            sections.append({"heading": current_heading, "content": body})

    return sections


def detect_entity_ids(text: str) -> list[str]:
    normalized = _normalize_text(text)
    matched: list[str] = []
    for spec in ENTITY_SPECS:
        aliases = spec["aliases"]
        if not isinstance(aliases, list):
            continue
        for alias in aliases:
            if _normalize_text(str(alias)) in normalized:
                matched.append(str(spec["id"]))
                break
    return matched


def build_graph_snapshot(collection_key: str = "all") -> dict[str, object]:
    nodes: dict[str, dict[str, object]] = {}
    edges: dict[tuple[str, str], dict[str, object]] = {}
    section_count = 0
    source_records = index_service.build_collection_source_records(collection_key)

    for record in source_records:
        path = record.get("path")
        if not isinstance(path, Path) or not path.exists():
            continue

        source_name = str(record.get("name", path.name))
        source_collection = str(record.get("collection_key", collection_key))
        sections = split_markdown_sections(path.read_text(encoding="utf-8"), source_name=source_name)
        for index, section in enumerate(sections, 1):
            entity_ids = detect_entity_ids(section["content"])
            if not entity_ids:
                continue
            section_count += 1

            for entity_id in entity_ids:
                spec = ENTITY_BY_ID.get(entity_id, {"label": entity_id})
                node = nodes.setdefault(
                    entity_id,
                    {
                        "id": entity_id,
                        "label": str(spec.get("label", entity_id)),
                        "sources": set(),
                        "collections": set(),
                    },
                )
                node["sources"].add(source_name)
                node["collections"].add(source_collection)

            for left, right in combinations(sorted(set(entity_ids)), 2):
                key = (left, right)
                edge = edges.setdefault(
                    key,
                    {
                        "source": left,
                        "target": right,
                        "weight": 0,
                        "collections": set(),
                        "evidence": [],
                    },
                )
                edge["weight"] = int(edge["weight"]) + 1
                edge["collections"].add(source_collection)
                evidence = edge["evidence"]
                if isinstance(evidence, list) and len(evidence) < 3:
                    evidence.append(
                        {
                            "source": source_name,
                            "heading": section["heading"],
                            "section_index": index,
                            "excerpt": section["content"][:240],
                        }
                    )

    serialized_nodes = []
    for node in nodes.values():
        serialized_nodes.append(
            {
                **node,
                "sources": sorted(node["sources"]),
                "collections": sorted(node["collections"]),
            }
        )

    serialized_edges = []
    for edge in edges.values():
        serialized_edges.append(
            {
                **edge,
                "collections": sorted(edge["collections"]),
            }
        )

    return {
        "nodes": sorted(serialized_nodes, key=lambda item: str(item["id"])),
        "edges": sorted(serialized_edges, key=lambda item: (str(item["source"]), str(item["target"]))),
        "stats": {
            "collection_key": collection_key,
            "source_docs": len(source_records),
            "section_hits": section_count,
            "nodes": len(serialized_nodes),
            "edges": len(serialized_edges),
        },
    }


def export_snapshot_jsonl(snapshot: dict[str, object], output_dir: Path) -> dict[str, str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    entities_path = output_dir / "entities.jsonl"
    relations_path = output_dir / "relations.jsonl"
    stats_path = output_dir / "ingest_stats.json"

    node_lines = [json.dumps(item, ensure_ascii=False) for item in snapshot.get("nodes", [])]
    edge_lines = [json.dumps(item, ensure_ascii=False) for item in snapshot.get("edges", [])]

    entities_path.write_text("\n".join(node_lines) + ("\n" if node_lines else ""), encoding="utf-8")
    relations_path.write_text("\n".join(edge_lines) + ("\n" if edge_lines else ""), encoding="utf-8")
    stats_path.write_text(json.dumps(snapshot.get("stats", {}), ensure_ascii=False, indent=2), encoding="utf-8")

    return {
        "entities": str(entities_path),
        "relations": str(relations_path),
        "stats": str(stats_path),
    }


def filter_graph_snapshot(snapshot: dict[str, object], collection_keys: list[str]) -> dict[str, object]:
    normalized_keys = [str(item).strip() for item in collection_keys if str(item).strip()]
    if not normalized_keys or DEFAULT_COLLECTION_KEY in normalized_keys:
        return snapshot

    allowed = set(normalized_keys)
    filtered_edges: list[dict[str, object]] = []
    matched_node_ids: set[str] = set()

    for edge in snapshot.get("edges", []):
        if not isinstance(edge, dict):
            continue
        edge_collections = {str(item) for item in edge.get("collections", [])}
        if edge_collections.isdisjoint(allowed):
            continue
        filtered_edges.append(edge)
        matched_node_ids.add(str(edge.get("source", "")))
        matched_node_ids.add(str(edge.get("target", "")))

    filtered_nodes: list[dict[str, object]] = []
    for node in snapshot.get("nodes", []):
        if not isinstance(node, dict):
            continue
        node_id = str(node.get("id", ""))
        node_collections = {str(item) for item in node.get("collections", [])}
        if node_id in matched_node_ids or not node_collections.isdisjoint(allowed):
            filtered_nodes.append(node)

    stats = dict(snapshot.get("stats", {}))
    stats.update(
        {
            "filtered": True,
            "collection_key": ",".join(normalized_keys),
            "nodes": len(filtered_nodes),
            "edges": len(filtered_edges),
        }
    )
    return {
        "nodes": filtered_nodes,
        "edges": filtered_edges,
        "stats": stats,
    }


def query_graph_snapshot(snapshot: dict[str, object], question: str, *, max_hops: int = 3) -> dict[str, object]:
    started = time.perf_counter()
    query_entities = detect_entity_ids(question)
    edges = snapshot.get("edges", [])
    adjacency: dict[str, list[dict[str, object]]] = {}
    for edge in edges:
        if not isinstance(edge, dict):
            continue
        source = str(edge.get("source", ""))
        target = str(edge.get("target", ""))
        adjacency.setdefault(source, []).append(edge)
        adjacency.setdefault(target, []).append(edge)

    seen_edge_keys: set[tuple[str, str]] = set()
    matched_entities = set(query_entities)
    visited_entities = set(query_entities)
    frontier = set(query_entities)
    selected_edges: list[dict[str, object]] = []

    for _depth in range(max_hops):
        next_frontier: set[str] = set()
        for entity_id in frontier:
            for edge in adjacency.get(entity_id, []):
                source = str(edge.get("source", ""))
                target = str(edge.get("target", ""))
                key = tuple(sorted((source, target)))
                if key in seen_edge_keys:
                    continue
                seen_edge_keys.add(key)
                selected_edges.append(edge)
                matched_entities.add(source)
                matched_entities.add(target)
                if source not in visited_entities:
                    next_frontier.add(source)
                if target not in visited_entities:
                    next_frontier.add(target)
        visited_entities.update(next_frontier)
        frontier = next_frontier

    relation_lines: list[str] = []
    for edge in sorted(selected_edges, key=lambda item: int(item.get("weight", 0)), reverse=True):
        source_id = str(edge.get("source", ""))
        target_id = str(edge.get("target", ""))
        evidence = edge.get("evidence", [])
        first = evidence[0] if isinstance(evidence, list) and evidence else {}
        source_label = str(ENTITY_BY_ID.get(source_id, {}).get("label", source_id))
        target_label = str(ENTITY_BY_ID.get(target_id, {}).get("label", target_id))
        relation_lines.append(
            f"{source_label} <-> {target_label} | weight={edge.get('weight', 0)} | "
            f"{first.get('source', '-')}: {first.get('heading', '-')}"
        )

    elapsed_ms = (time.perf_counter() - started) * 1000.0
    return {
        "question": question,
        "query_entities": sorted(query_entities),
        "matched_entities": sorted(matched_entities),
        "relations": relation_lines[:12],
        "latency_ms": round(elapsed_ms, 3),
    }


def answer_graph_snapshot(snapshot: dict[str, object], question: str, *, max_hops: int = 3) -> dict[str, object]:
    result = query_graph_snapshot(snapshot, question, max_hops=max_hops)
    query_entities = [_entity_display_name(entity_id) for entity_id in result["query_entities"]]
    matched_entities = [_entity_display_name(entity_id) for entity_id in result["matched_entities"]]
    relation_lines = [str(line) for line in result["relations"][:6]]

    lines = [
        f"질문 재진술: {question}",
        "그래프 스냅샷 기준 관계망 요약입니다.",
        f"핵심 엔티티: {', '.join(query_entities) if query_entities else '질문에서 직접 감지된 엔티티 없음'}",
        f"확장 엔티티: {', '.join(matched_entities[:8]) if matched_entities else '-'}",
        "관계 근거:",
    ]
    if relation_lines:
        lines.extend(f"- {line}" for line in relation_lines)
    else:
        lines.append("- 직접 연결된 relation evidence를 찾지 못했습니다.")

    return {
        **result,
        "answer": "\n".join(lines),
        "query_entity_labels": query_entities,
        "matched_entity_labels": matched_entities,
    }


def benchmark_graph_candidates(snapshot: dict[str, object], *, max_hops: int = 2) -> dict[str, object]:
    results: list[dict[str, object]] = []
    latency_values: list[float] = []
    hit_ratios: list[float] = []

    for spec in GRAPH_CANDIDATE_SPECS:
        result = query_graph_snapshot(snapshot, str(spec["question"]), max_hops=max_hops)
        expected_entities = [str(item) for item in spec.get("expected_entities", [])]
        matched_entities = set(result["matched_entities"])
        hit_count = sum(1 for item in expected_entities if item in matched_entities)
        hit_ratio = round((hit_count / len(expected_entities)), 4) if expected_entities else 0.0
        results.append(
            {
                "id": spec["id"],
                "question": spec["question"],
                "query_entities": result["query_entities"],
                "matched_entities": result["matched_entities"],
                "relation_count": len(result["relations"]),
                "relations": result["relations"],
                "latency_ms": result["latency_ms"],
                "expected_entities": expected_entities,
                "expected_entity_hits": hit_count,
                "expected_entity_hit_ratio": hit_ratio,
            }
        )
        latency_values.append(float(result["latency_ms"]))
        hit_ratios.append(hit_ratio)

    avg_latency = round(sum(latency_values) / len(latency_values), 3) if latency_values else 0.0
    avg_hit_ratio = round(sum(hit_ratios) / len(hit_ratios), 4) if hit_ratios else 0.0
    return {
        "results": results,
        "summary": {
            "questions": len(results),
            "avg_latency_ms": avg_latency,
            "avg_expected_entity_hit_ratio": avg_hit_ratio,
            "max_hops": max_hops,
        },
    }
