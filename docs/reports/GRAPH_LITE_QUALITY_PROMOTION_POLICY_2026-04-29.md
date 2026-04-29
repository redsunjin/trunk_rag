# Graph-Lite Quality Promotion Policy (2026-04-29)

## Scope

- Loop: `LOOP-112 Graph-lite Quality promotion decision and operator policy`
- Inputs:
  - `docs/reports/GRAPH_LITE_ACTIVE_DOC_QUALITY_DRILL_2026-04-29.md`
  - `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-04-29_GRAPH_LITE_ACTIVE_DOC_QWEN.md`
  - `docs/reports/RAG_QUALITY_MODEL_COMPARISON_2026-04-29_GRAPH_LITE_ACTIVE_DOC_QWEN.md`
- Boundary: policy and operator handoff only. No Balanced default behavior change, no model default change, no paid API, and no full Neo4j/GraphRAG reactivation.

## Decision

| Area | Decision | Reason |
| --- | --- | --- |
| Quality opt-in graph-lite | Go | active-doc snapshot + qwen Quality graph-candidate gate passed. |
| Balanced default graph-lite | No-Go | evidence is relation-heavy and Quality-specific; default path must stay low-latency and predictable. |
| qwen Quality candidate | Conditional Go | `qwen3.5:9b-nvfp4` passed graph-candidate Quality gate, but remains an advanced Quality candidate, not the default model. |
| Snapshot automation | No-Go for now | manual build/set flow is enough until real managed docs create churn. |
| Full GraphRAG/Neo4j | No-Go | graph-lite is still a local sidecar, not a graph database product track. |

## Evidence Summary

- Active-doc snapshot build:
  - source_docs: `5`
  - section_hits: `21`
  - entities: `20`
  - relations: `48`
- Graph-lite retrieval benchmark:
  - graph-candidate hits: `3/3`
  - fallbacks: `0`
  - avg_latency_ms: `0.179`
- Quality answer eval with qwen:
  - graph-candidate pass_rate: `1.0`
  - avg_weighted_score: `0.9167`
  - p95_latency_ms: `4479.486`
  - support_pass_rate: `1.0`
  - source_route_pass_rate: `1.0`
- Graph-lite observation:
  - all graph-candidate cases reported `graph_lite=hit`
  - header: `hit`
  - relations: `8`
  - context_added: `True`
- Compare gate:
  - outcome: `ready`
  - selected_candidate: `ollama:qwen3.5:9b-nvfp4`
  - p95_latency_ms: `4468.718`

## Operator Flow

1. Build or refresh the graph-lite snapshot:

   ```bash
   ./.venv/bin/python scripts/build_graph_lite_snapshot.py --output-dir chroma_db/graph_lite_snapshot
   ```

2. Start the server with the snapshot path:

   ```bash
   DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR=chroma_db/graph_lite_snapshot ./.venv/bin/python app_api.py
   ```

3. Use `/app` with `Quality` mode for relation-heavy questions.

4. Check answer metadata:
   - `graph-lite=hit`: relation context was appended.
   - `relations=N`: relation evidence count.
   - `context=added`: graph-lite block was added to the RAG context.
   - `graph-lite=fallback`: normal vector context was used because snapshot/no-hit/error prevented graph-lite context.
   - `graph-lite=disabled`: expected for Balanced/default flows.

5. If the snapshot is missing or stale:
   - keep answering through the vector path;
   - rebuild snapshot from current seed + managed active markdown;
   - do not block the default `/query` path.

## Promotion Guardrails

- Graph-lite remains opt-in to `quality_mode=quality` or `quality_stage=quality`.
- Balanced mode must not load graph-lite by default.
- Fallback must preserve answer generation.
- UI must keep exposing hit/fallback/disabled state so operators can distinguish graph evidence from vector-only evidence.
- Re-run graph-candidate Quality eval after meaningful document changes before changing the policy.

## Next Step

The next queued loop can evaluate a browser companion PoC scope. That should stay separate from the graph-lite policy: browser extension work is a new access surface, not a replacement for the local Trunk RAG runtime.

