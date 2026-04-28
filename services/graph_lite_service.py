from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path

from core.settings import DEFAULT_COLLECTION_KEY

GRAPH_LITE_CONTRACT_VERSION = "graph_lite.relation_snapshot.v1"
GRAPH_LITE_RESULT_MODE = "graph_lite"

DEFAULT_ENTITIES_FILE = "entities.jsonl"
DEFAULT_RELATIONS_FILE = "relations.jsonl"
DEFAULT_STATS_FILE = "ingest_stats.json"
GRAPH_LITE_SNAPSHOT_DIR_ENV_KEY = "DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR"
DEFAULT_SNAPSHOT_DIR = Path("docs/reports/graphrag_snapshot_2026-03-17")
GRAPH_LITE_DEFAULT_MAX_HOPS = 2
GRAPH_LITE_DEFAULT_LIMIT = 8
GRAPH_LITE_DEFAULT_CONTEXT_CHARS = 1200

RELATION_HEAVY_KEYWORDS = (
    "관계",
    "관계망",
    "연결",
    "연쇄",
    "이어",
    "영향",
    "확산",
    "흐름",
    "경로",
    "네트워크",
    "비교",
    "차이",
    "공통점",
    "역할",
    "relation",
    "network",
    "chain",
    "influence",
    "compare",
    "connection",
)

KNOWN_ENTITY_ALIASES: dict[str, tuple[str, ...]] = {
    "newton": ("뉴턴", "newton"),
    "voltaire": ("볼테르", "voltaire"),
    "leibniz": ("라이프니츠", "leibniz"),
    "galileo": ("갈릴레오", "galileo"),
    "medici": ("메디치", "medici"),
    "ecole_polytechnique": ("에콜 폴리테크니크", "ecole polytechnique", "école polytechnique"),
    "humboldt_university": ("훔볼트 대학", "훔볼트 대학교", "베를린 대학", "humboldt university"),
    "royal_society": ("왕립학회", "royal society"),
    "padua_university": ("파도바 대학", "padua university"),
    "bologna_university": ("볼로냐", "볼로냐 대학", "bologna"),
    "magnus_lab": ("마그누스 실험실", "구스타프 마그누스", "gustav magnus", "magnus"),
    "helmholtz": ("헬름홀츠", "helmholtz"),
    "siemens": ("지멘스", "siemens"),
    "german_physical_society": ("독일 물리학회", "dpg", "german physical society"),
    "max_planck_institute": ("막스 플랑크 연구소", "max planck institute"),
    "gottingen": ("괴팅겐", "göttingen", "gottingen"),
    "french_revolution": ("프랑스 혁명", "french revolution"),
    "napoleonic_wars": ("나폴레옹 전쟁", "napoleonic wars"),
    "great_fire_london": ("런던 대화재", "great fire of london"),
    "enlightenment": ("계몽주의", "enlightenment"),
}


@dataclass(frozen=True)
class GraphLiteEntity:
    id: str
    label: str
    aliases: tuple[str, ...]
    sources: tuple[str, ...]
    collections: tuple[str, ...]


@dataclass(frozen=True)
class GraphLiteRelation:
    source: str
    target: str
    predicate: str
    weight: int
    collections: tuple[str, ...]
    evidence: tuple[dict[str, object], ...]


@dataclass(frozen=True)
class GraphLiteSnapshot:
    entities: dict[str, GraphLiteEntity]
    relations: tuple[GraphLiteRelation, ...]
    stats: dict[str, object]
    source_dir: str | None = None


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def _as_string_tuple(value: object) -> tuple[str, ...]:
    if isinstance(value, list):
        items = [str(item).strip() for item in value if str(item).strip()]
        return tuple(dict.fromkeys(items))
    if isinstance(value, tuple):
        items = [str(item).strip() for item in value if str(item).strip()]
        return tuple(dict.fromkeys(items))
    if isinstance(value, str) and value.strip():
        return (value.strip(),)
    return ()


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        raise FileNotFoundError(f"Graph-lite snapshot file not found: {path}")

    records: list[dict[str, object]] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = raw_line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_number}") from exc
        if not isinstance(payload, dict):
            raise ValueError(f"JSONL record must be an object at {path}:{line_number}")
        records.append(payload)
    return records


def _load_stats(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    payload = json.loads(path.read_text(encoding="utf-8") or "{}")
    return payload if isinstance(payload, dict) else {}


def _build_entity(record: dict[str, object]) -> GraphLiteEntity:
    entity_id = str(record.get("id", "")).strip()
    if not entity_id:
        raise ValueError("Graph-lite entity record requires id")

    label = str(record.get("label", entity_id)).strip() or entity_id
    alias_candidates = [
        entity_id,
        label,
        *KNOWN_ENTITY_ALIASES.get(entity_id, ()),
        *_as_string_tuple(record.get("aliases")),
    ]
    aliases = tuple(dict.fromkeys(item for item in alias_candidates if item.strip()))
    return GraphLiteEntity(
        id=entity_id,
        label=label,
        aliases=aliases,
        sources=_as_string_tuple(record.get("sources")),
        collections=_as_string_tuple(record.get("collections")),
    )


def _build_relation(record: dict[str, object]) -> GraphLiteRelation:
    source = str(record.get("source", "")).strip()
    target = str(record.get("target", "")).strip()
    if not source or not target:
        raise ValueError("Graph-lite relation record requires source and target")

    raw_evidence = record.get("evidence", [])
    evidence = tuple(item for item in raw_evidence if isinstance(item, dict)) if isinstance(raw_evidence, list) else ()
    return GraphLiteRelation(
        source=source,
        target=target,
        predicate=str(record.get("predicate", "co_occurs")).strip() or "co_occurs",
        weight=max(1, int(record.get("weight", 1) or 1)),
        collections=_as_string_tuple(record.get("collections")),
        evidence=evidence,
    )


def load_relation_snapshot(
    snapshot_dir: str | Path,
    *,
    entities_file: str = DEFAULT_ENTITIES_FILE,
    relations_file: str = DEFAULT_RELATIONS_FILE,
    stats_file: str = DEFAULT_STATS_FILE,
) -> GraphLiteSnapshot:
    base_dir = Path(snapshot_dir)
    entity_records = _read_jsonl(base_dir / entities_file)
    relation_records = _read_jsonl(base_dir / relations_file)
    built_entities = [_build_entity(record) for record in entity_records]
    entities = {entity.id: entity for entity in built_entities}
    relations = tuple(_build_relation(record) for record in relation_records)
    stats = _load_stats(base_dir / stats_file)
    stats.setdefault("contract_version", GRAPH_LITE_CONTRACT_VERSION)
    stats.setdefault("nodes", len(entities))
    stats.setdefault("edges", len(relations))
    return GraphLiteSnapshot(
        entities=entities,
        relations=relations,
        stats=stats,
        source_dir=str(base_dir),
    )


def get_default_snapshot_dir() -> Path:
    configured = os.getenv(GRAPH_LITE_SNAPSHOT_DIR_ENV_KEY, "").strip()
    if configured:
        return Path(configured)
    return Path(__file__).resolve().parents[1] / DEFAULT_SNAPSHOT_DIR


def load_default_relation_snapshot() -> GraphLiteSnapshot:
    return load_relation_snapshot(get_default_snapshot_dir())


def entity_label(snapshot: GraphLiteSnapshot, entity_id: str) -> str:
    entity = snapshot.entities.get(entity_id)
    return entity.label if entity else entity_id


def detect_query_entities(snapshot: GraphLiteSnapshot, question: str) -> list[str]:
    normalized_question = _normalize_text(question)
    matched: list[str] = []
    for entity_id, entity in snapshot.entities.items():
        for alias in entity.aliases:
            normalized_alias = _normalize_text(alias)
            if normalized_alias and normalized_alias in normalized_question:
                matched.append(entity_id)
                break
    return sorted(dict.fromkeys(matched))


def detect_relation_query_intent(snapshot: GraphLiteSnapshot, question: str) -> dict[str, object]:
    normalized_question = _normalize_text(question)
    entity_ids = detect_query_entities(snapshot, question)
    keyword_hits = [keyword for keyword in RELATION_HEAVY_KEYWORDS if keyword in normalized_question]
    relation_heavy = len(entity_ids) >= 2 and bool(keyword_hits)
    reason = "keyword_and_multi_entity" if relation_heavy else "not_relation_heavy"
    if not entity_ids:
        reason = "no_query_entities"
    elif len(entity_ids) < 2:
        reason = "single_query_entity"
    elif not keyword_hits:
        reason = "no_relation_keyword"
    return {
        "relation_heavy": relation_heavy,
        "reason": reason,
        "entity_ids": entity_ids,
        "entity_labels": [entity_label(snapshot, item) for item in entity_ids],
        "keyword_hits": keyword_hits,
    }


def _relation_matches_collections(relation: GraphLiteRelation, collection_keys: list[str] | None) -> bool:
    if not collection_keys:
        return True
    normalized_keys = {str(item).strip() for item in collection_keys if str(item).strip()}
    if not normalized_keys or DEFAULT_COLLECTION_KEY in normalized_keys:
        return True
    if not relation.collections:
        return False
    return not normalized_keys.isdisjoint(set(relation.collections))


def _build_adjacency(relations: list[GraphLiteRelation]) -> dict[str, list[GraphLiteRelation]]:
    adjacency: dict[str, list[GraphLiteRelation]] = {}
    for relation in relations:
        adjacency.setdefault(relation.source, []).append(relation)
        adjacency.setdefault(relation.target, []).append(relation)
    return adjacency


def _evidence_text(relation: GraphLiteRelation) -> str:
    parts: list[str] = []
    for evidence in relation.evidence[:2]:
        parts.extend(
            [
                str(evidence.get("source", "")),
                str(evidence.get("heading", "")),
                str(evidence.get("excerpt", "")),
            ]
        )
    return " ".join(parts).lower()


def _score_relation(
    snapshot: GraphLiteSnapshot,
    relation: GraphLiteRelation,
    seed_entities: set[str],
    keyword_hits: list[str],
) -> float:
    endpoints = {relation.source, relation.target}
    seed_overlap = len(endpoints & seed_entities)
    score = float(relation.weight)
    score += seed_overlap * 3.0
    if seed_overlap == 2:
        score += 2.0

    relation_text = " ".join(
        [
            entity_label(snapshot, relation.source),
            entity_label(snapshot, relation.target),
            relation.predicate,
            _evidence_text(relation),
        ]
    ).lower()
    score += sum(0.35 for keyword in keyword_hits if keyword.lower() in relation_text)
    return round(score, 4)


def _relation_to_payload(
    snapshot: GraphLiteSnapshot,
    relation: GraphLiteRelation,
    score: float,
) -> dict[str, object]:
    return {
        "source": relation.source,
        "source_label": entity_label(snapshot, relation.source),
        "target": relation.target,
        "target_label": entity_label(snapshot, relation.target),
        "predicate": relation.predicate,
        "weight": relation.weight,
        "score": score,
        "collections": list(relation.collections),
        "evidence": list(relation.evidence),
    }


def query_relation_snapshot(
    snapshot: GraphLiteSnapshot,
    question: str,
    *,
    collection_keys: list[str] | None = None,
    max_hops: int = 2,
    limit: int = 8,
    force: bool = False,
) -> dict[str, object]:
    started = time.perf_counter()
    intent = detect_relation_query_intent(snapshot, question)
    query_entities = [str(item) for item in intent.get("entity_ids", [])]
    keyword_hits = [str(item) for item in intent.get("keyword_hits", [])]
    if not force and not bool(intent["relation_heavy"]):
        return {
            "contract_version": GRAPH_LITE_CONTRACT_VERSION,
            "mode": GRAPH_LITE_RESULT_MODE,
            "status": "fallback",
            "fallback_used": True,
            "fallback_reason": str(intent["reason"]),
            "question": question,
            "query_entities": query_entities,
            "matched_entities": query_entities,
            "relations": [],
            "context": "",
            "intent": intent,
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }

    if not query_entities:
        return {
            "contract_version": GRAPH_LITE_CONTRACT_VERSION,
            "mode": GRAPH_LITE_RESULT_MODE,
            "status": "fallback",
            "fallback_used": True,
            "fallback_reason": "no_query_entities",
            "question": question,
            "query_entities": [],
            "matched_entities": [],
            "relations": [],
            "context": "",
            "intent": intent,
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }

    filtered_relations = [
        relation for relation in snapshot.relations if _relation_matches_collections(relation, collection_keys)
    ]
    adjacency = _build_adjacency(filtered_relations)
    seed_entities = set(query_entities)
    selected: dict[tuple[str, str, str], GraphLiteRelation] = {}
    visited_entities = set(seed_entities)
    frontier = set(seed_entities)

    for _depth in range(max(1, int(max_hops))):
        next_frontier: set[str] = set()
        for entity_id in frontier:
            for relation in adjacency.get(entity_id, []):
                key = tuple(sorted((relation.source, relation.target)) + [relation.predicate])
                selected[key] = relation
                for endpoint in (relation.source, relation.target):
                    if endpoint not in visited_entities:
                        next_frontier.add(endpoint)
        visited_entities.update(next_frontier)
        frontier = next_frontier
        if not frontier:
            break

    if not selected:
        return {
            "contract_version": GRAPH_LITE_CONTRACT_VERSION,
            "mode": GRAPH_LITE_RESULT_MODE,
            "status": "fallback",
            "fallback_used": True,
            "fallback_reason": "no_graph_hit",
            "question": question,
            "query_entities": query_entities,
            "matched_entities": sorted(visited_entities),
            "relations": [],
            "context": "",
            "intent": intent,
            "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
        }

    scored = [
        (
            _score_relation(snapshot, relation, seed_entities, keyword_hits),
            relation,
        )
        for relation in selected.values()
    ]
    scored.sort(key=lambda item: (-item[0], item[1].source, item[1].target, item[1].predicate))
    relation_payloads = [_relation_to_payload(snapshot, relation, score) for score, relation in scored[: max(1, limit)]]
    matched_entities = set(query_entities)
    for item in relation_payloads:
        matched_entities.add(str(item["source"]))
        matched_entities.add(str(item["target"]))

    confidence = min(1.0, 0.35 + len(query_entities) * 0.1 + len(relation_payloads) * 0.06)
    result = {
        "contract_version": GRAPH_LITE_CONTRACT_VERSION,
        "mode": GRAPH_LITE_RESULT_MODE,
        "status": "hit",
        "fallback_used": False,
        "fallback_reason": None,
        "question": question,
        "query_entities": query_entities,
        "matched_entities": sorted(matched_entities),
        "matched_entity_labels": [entity_label(snapshot, item) for item in sorted(matched_entities)],
        "relations": relation_payloads,
        "confidence": round(confidence, 4),
        "intent": intent,
        "latency_ms": round((time.perf_counter() - started) * 1000.0, 3),
    }
    return {**result, "context": build_graph_lite_context(result)}


def build_graph_lite_context(result: dict[str, object], *, max_chars: int = 1200) -> str:
    if result.get("status") != "hit":
        return ""

    lines = ["[Graph-Lite Relations]"]
    relations = result.get("relations", [])
    if not isinstance(relations, list):
        return ""

    for index, relation in enumerate(relations, 1):
        if not isinstance(relation, dict):
            continue
        source_label = str(relation.get("source_label", relation.get("source", "")))
        target_label = str(relation.get("target_label", relation.get("target", "")))
        predicate = str(relation.get("predicate", "co_occurs"))
        weight = relation.get("weight", 1)
        score = relation.get("score", 0)
        lines.append(
            f"[graph-lite:{index}] {source_label} --{predicate}--> {target_label} "
            f"| weight={weight} | score={score}"
        )

        evidence = relation.get("evidence", [])
        if isinstance(evidence, list) and evidence:
            first = evidence[0] if isinstance(evidence[0], dict) else {}
            source_doc = str(first.get("source", "-"))
            heading = str(first.get("heading", "-"))
            excerpt = re.sub(r"\s+", " ", str(first.get("excerpt", ""))).strip()
            if len(excerpt) > 280:
                excerpt = excerpt[:277].rstrip() + "..."
            lines.append(f"source={source_doc} h2={heading}")
            if excerpt:
                lines.append(f"evidence={excerpt}")

    context = "\n".join(lines).strip()
    if len(context) <= max_chars:
        return context
    return context[:max_chars].rstrip()


def append_graph_lite_context(base_context: str, graph_result: dict[str, object], *, max_chars: int = 1200) -> str:
    graph_context = build_graph_lite_context(graph_result, max_chars=max_chars)
    if not graph_context:
        return base_context
    if not base_context.strip():
        return graph_context
    return f"{base_context.rstrip()}\n\n{graph_context}"
