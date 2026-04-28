# Graph-Lite Relation Sidecar Contract

## Status

- Status: PoC contract, not default product runtime.
- Scope: local JSONL relation snapshot loading and in-memory relation retrieval.
- Non-scope: Neo4j, full GraphRAG orchestration, network calls, paid APIs, or automatic `/query` replacement.

## Purpose

Graph-lite gives Trunk RAG a small relation-aware retrieval layer for questions where vector search alone may find relevant chunks but miss the relationship path between entities.

The sidecar output is intended to be appended to RAG context only when a question is relation-heavy and relation evidence is found. Existing vector retrieval remains the fallback and the default path.

## Snapshot Files

The minimal local snapshot is a directory with:

- `entities.jsonl`
- `relations.jsonl`
- `ingest_stats.json` optional

Entity record:

```json
{
  "id": "newton",
  "label": "Newton",
  "aliases": ["뉴턴", "newton"],
  "sources": ["uk.md"],
  "collections": ["uk"]
}
```

Relation record:

```json
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
      "excerpt": "원문 근거 일부"
    }
  ]
}
```

## Query Detector

A query is graph-lite eligible when both are true:

- at least two known entities are detected
- relation-heavy keywords are present, such as `관계`, `관계망`, `연결`, `연쇄`, `영향`, `확산`, `흐름`, `네트워크`, `비교`

If the detector does not match, graph-lite returns fallback metadata without changing the vector/RAG path.

## Runtime Result Contract

Hit:

```json
{
  "contract_version": "graph_lite.relation_snapshot.v1",
  "mode": "graph_lite",
  "status": "hit",
  "fallback_used": false,
  "fallback_reason": null,
  "query_entities": ["newton", "voltaire"],
  "matched_entities": ["enlightenment", "newton", "voltaire"],
  "relations": [
    {
      "source": "newton",
      "source_label": "Newton",
      "target": "voltaire",
      "target_label": "Voltaire",
      "predicate": "influenced",
      "weight": 3,
      "score": 11.0,
      "collections": ["uk", "fr"],
      "evidence": []
    }
  ],
  "context": "[Graph-Lite Relations]..."
}
```

Fallback:

```json
{
  "contract_version": "graph_lite.relation_snapshot.v1",
  "mode": "graph_lite",
  "status": "fallback",
  "fallback_used": true,
  "fallback_reason": "no_graph_hit",
  "relations": [],
  "context": ""
}
```

Fallback reasons:

- `no_query_entities`
- `single_query_entity`
- `no_relation_keyword`
- `not_relation_heavy`
- `no_graph_hit`

## Integration Rule

The current PoC exposes an internal helper:

```python
append_graph_lite_context(base_context, graph_result)
```

This helper appends relation evidence only when `graph_result.status == "hit"`. If graph-lite falls back, the original context is returned unchanged.

Default `/query` integration is intentionally not enabled in this loop. A future integration should make graph-lite opt-in through Balanced/Quality mode or an explicit advanced relation mode, and must keep vector fallback active.

## Validation

Minimum checks for this PoC:

- relation snapshot loading
- relation-heavy detector behavior
- relation search with collection filters
- no-hit and non relation-heavy fallback
- context append no-op on fallback
