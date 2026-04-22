# V1.5 reindex live adapter guarded live executor smoke evidence draft

Date: 2026-04-22
Loop: `LOOP-067`

## Decision

`Go` for post-smoke enablement checkpoint review.

The guarded live executor command now proves the explicit local-only `guarded_live_executor` path can call `index_service.reindex()` and still keep the current top-level apply response on the blocked `MUTATION_APPLY_NOT_ENABLED` surface.

Top-level success promotion remains disabled.

## Command

```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 \
  DOC_RAG_MUTATION_AUDIT_BACKEND=local_file \
  DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag-guarded-live-smoke \
  ./.venv/bin/python scripts/smoke_agent_runtime.py \
  --opt-in-live-binding \
  --opt-in-live-binding-stage-guarded
```

## Evidence

Final smoke run:

- `ok=true`
- `requested_live_binding=true`
- `requested_live_binding_stage=guarded_live_executor`
- apply check: `write_tool_apply_not_enabled`
- apply error code: `MUTATION_APPLY_NOT_ENABLED`
- apply blocked by: `mutation_apply_guard`
- audit sink: `local_file_append_only`
- audit sequence id: `18`
- audit path: `/tmp/trunk_rag-guarded-live-smoke/audit-20260422.jsonl`
- executor: `reindex_mutation_adapter_live`
- selection state: `guarded_live_executor`
- runtime handler: `index_service.reindex`
- runtime handler invoked: `true`
- runtime chunks: `37`
- runtime vectors: `37`
- runtime collection: `w2_007_header_rag`
- runtime scope: `default_runtime_only`
- top-level promotion enabled: `false`
- top-level success route eligible: `true`
- future success target: `result`, `top_level_ok=true`

## Implementation Note

The first guarded smoke attempt selected `guarded_live_executor` and invoked `index_service.reindex()`, but no `mutation_executor_result` was produced. Direct diagnosis showed Chroma rejected list metadata:

```text
Expected metadata value to be a str, int, float or bool, got ['sample-pack', 'summary'] which is a list
```

`services/index_service.py` now keeps source-record metadata intact, but normalizes metadata only for vectorstore ingest. Complex values such as list/dict are serialized as JSON strings before calling Chroma.

The smoke harness was also tightened so a guarded stage apply check is not considered successful unless runtime sidecar evidence is present.

## Verification

- `./.venv/bin/python -m pytest -q tests/test_index_service.py tests/test_smoke_agent_runtime.py tests/test_mutation_executor_service.py` -> `36 passed`
- guarded smoke command above -> `ok=true`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`
- `git diff --check` -> passed

## Remaining Gate

The command proves guarded local execution, but it does not open user/public apply success. The next checkpoint should decide whether top-level promotion can move from draft evidence to implementation, or whether audit detail/rollback evidence must be strengthened first.
