# Graph-Lite Relation Sidecar PoC Report (2026-04-28)

## Scope
- Local JSONL relation snapshot loader and in-memory relation search only.
- No Neo4j, external DB, network call, paid API, or default `/query` route integration.
- This measures graph-lite retrieval viability before answer-generation integration.

## Summary
- fixture_bucket: `graph-candidate`
- snapshot_dir: `docs/reports/graphrag_snapshot_2026-03-17`
- questions: `3`
- hits: `3`
- fallbacks: `0`
- avg_latency_ms: `0.194`
- avg_relation_count: `8.0`

## Results
### GQ-09
- status: `hit`
- fallback_reason: `-`
- query_entities: `enlightenment, newton, voltaire`
- matched_entities: `enlightenment, helmholtz, leibniz, newton, siemens, voltaire`
- relation_count: `8`
- latency_ms: `0.199`
### GQ-12
- status: `hit`
- fallback_reason: `-`
- query_entities: `german_physical_society, helmholtz, magnus_lab, siemens`
- matched_entities: `german_physical_society, helmholtz, humboldt_university, magnus_lab, newton, siemens`
- relation_count: `8`
- latency_ms: `0.166`
### GQ-15
- status: `hit`
- fallback_reason: `-`
- query_entities: `ecole_polytechnique, humboldt_university, padua_university, royal_society`
- matched_entities: `bologna_university, ecole_polytechnique, french_revolution, german_physical_society, great_fire_london, helmholtz, humboldt_university, magnus_lab, napoleonic_wars, padua_university, royal_society, siemens`
- relation_count: `8`
- latency_ms: `0.216`

## Interpretation
- A hit means graph-lite found relation evidence that can be appended to RAG context.
- A fallback is expected for non relation-heavy questions or missing entity/relation coverage.
- Answer quality still requires a separate `/query` quality comparison after graph context is wired in.
