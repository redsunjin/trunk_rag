# V1.5 reindex live adapter post-executor audit evidence draft

Date: 2026-04-22
Loop: `LOOP-071`

## Decision

`Go` for post-audit enablement checkpoint review.

Guarded executor success/failure can now leave a post-executor append-only audit record linked to the pre-executor audit receipt.

## Implementation

1. `services/tool_middleware_service.py`
   - Added `MUTATION_EXECUTOR_POST_AUDIT_SCHEMA_VERSION`.
   - Added `ToolExecutionState.mutation_executor_audit_receipt`.
   - Builds a sanitized post-executor audit record after guarded executor success or failure.
   - Appends the post-executor record through the configured append-only audit sink.
   - Exposes `mutation_executor_audit_receipt` in blocked apply response and `execution_trace.contracts`.

2. `scripts/smoke_agent_runtime.py`
   - Smoke summary now includes `mutation_executor_audit_receipt`.

3. Tests
   - Success path verifies the post-executor receipt links to the executor result audit sequence.
   - Failure path verifies the post-executor audit record contains sanitized failure outcome metadata.
   - Audit sink validation accepts post-executor audit metadata without raw actor/payload fields.

## Live Evidence

Guarded smoke command:

```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 \
  DOC_RAG_MUTATION_AUDIT_BACKEND=local_file \
  DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag-guarded-live-smoke \
  ./.venv/bin/python scripts/smoke_agent_runtime.py \
  --opt-in-live-binding \
  --opt-in-live-binding-stage-guarded
```

Observed output:

- `ok=true`
- apply error code: `MUTATION_APPLY_NOT_ENABLED`
- pre-executor audit sequence id: `24`
- post-executor audit sequence id: `25`
- post-executor record kind: `mutation_executor_post_execution`
- post-executor record schema: `v1.5.mutation_executor_post_execution_audit.v1`
- runtime chunks: `37`
- runtime vectors: `37`
- top-level promotion enabled: `false`

Audit tail confirmed the durable record:

- `record.source_schema_version=v1.5.mutation_executor_post_execution_audit.v1`
- `record.audit.events[0].event=mutation_executor.completed`
- `record.audit.events[0].pre_executor_audit_sequence_id=24`
- `record.mutation_executor_audit.result.runtime_chunks=37`
- `record.mutation_executor_audit.result.runtime_vectors=37`

## Verification

- `./.venv/bin/python -m pytest -q tests/test_tool_middleware_service.py tests/test_tool_audit_sink_service.py tests/test_smoke_agent_runtime.py` -> `31 passed`
- guarded smoke command above -> `ok=true`

## Remaining Gate

Success/failure response sidecars and post-executor durable audit evidence now exist. Top-level promotion still remains disabled until the next checkpoint decides whether rollback drill evidence is required before opening the apply success/failure gate.
