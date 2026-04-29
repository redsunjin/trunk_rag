# Graph-Lite Active-Doc Quality Drill (2026-04-29)

## Scope

- Loop: `LOOP-110 Graph-lite active-doc Quality drill and fixture seed`
- Purpose: confirm that the current seed + managed active markdown sources can generate a graph-lite snapshot that remains useful for `Quality` graph-candidate retrieval.
- Boundary: local JSONL snapshot build and in-memory graph-lite benchmark only. No Neo4j, external database, paid API, LLM relation extraction, or Balanced default graph-lite promotion.

## Snapshot Build

- Command: `./.venv/bin/python scripts/build_graph_lite_snapshot.py --output-dir /tmp/trunk_rag_graph_lite_snapshot_loop110`
- Output dir: `/tmp/trunk_rag_graph_lite_snapshot_loop110`
- Source docs: `5`
- Section hits: `21`
- Entities: `20`
- Relations: `48`
- Contract: `graph_lite.relation_snapshot.v1`
- Builder: `graph_lite_snapshot_builder.v1`

## Benchmark

- Command: `./.venv/bin/python scripts/benchmark_graph_lite_sidecar.py --snapshot-dir /tmp/trunk_rag_graph_lite_snapshot_loop110 --output-json /tmp/graph_lite_active_doc_loop110.json --output-report /tmp/GRAPH_LITE_ACTIVE_DOC_LOOP110.md`
- Fixture bucket: `graph-candidate`
- Questions: `3`
- Hits: `3`
- Fallbacks: `0`
- Average latency: `0.179ms`
- Average relation count: `8.0`
- Max hops: `2`
- Limit: `8`

## Case Results

| id | relation shape | status | relation_count | latency_ms |
| --- | --- | --- | --- | --- |
| `GQ-09` | scientist -> event -> intellectual diffusion | `hit` | `8` | `0.181` |
| `GQ-12` | lab -> people -> society -> industry | `hit` | `8` | `0.161` |
| `GQ-15` | country -> institution -> scientist network | `hit` | `8` | `0.195` |

## Interpretation

- The active-doc snapshot builder reproduces the LOOP-108 shape and keeps graph-candidate retrieval viable without depending on the archived GraphRAG snapshot.
- `LOOP-109` UI status exposure now has a real local drill to point to: Quality graph-lite can report `hit`, relation count, and context-added state when the snapshot is available.
- This does not promote graph-lite to the Balanced default path. The next step is a Quality answer eval refresh using the generated active-doc snapshot.

