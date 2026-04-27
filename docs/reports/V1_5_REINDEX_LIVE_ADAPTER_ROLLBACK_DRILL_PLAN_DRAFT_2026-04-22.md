# V1.5 reindex live adapter rollback drill plan draft

Date: 2026-04-22
Loop: `LOOP-077`

## Decision

`Go` for a local-only rollback drill harness draft.

This plan does not open default/public promotion. It defines the evidence required before an actual rollback drill can be run safely.

## Purpose

The guarded `reindex` live adapter mutates derivative vector state. Its rollback hint is `rebuild_from_source_documents`, so the drill must prove that an operator can:

1. capture the vector/index state before a guarded reindex,
2. run the explicit local-only guarded reindex path,
3. verify append-only pre/post audit linkage,
4. rebuild the same collection from source documents,
5. confirm the recovered vector/index state is healthy.

## Scope

In scope:

- `reindex` only
- local audit backend only
- default runtime collection only unless a later harness explicitly takes a collection argument
- source-document rebuild recovery
- vector count and smoke-level health verification

Out of scope:

- default/public promotion
- upload review live execution
- automated deletion of source documents
- destructive tests against non-local operator data
- rollback drill for non-derivative state

## Preconditions

Before running the drill:

- `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file`
- `DOC_RAG_MUTATION_AUDIT_DIR` points to a disposable local runtime tree
- `DOC_RAG_AGENT_MUTATION_EXECUTION=1`
- default smoke passes
- guarded blocked smoke passes
- guarded top-level promotion smoke passes
- source documents for the target collection are present
- operator confirms the target collection is local test/runtime data

## Required Evidence

Capture before the guarded reindex:

- target collection key
- vector count
- collection status from `health_check` or equivalent service call
- audit sequence state if present
- source document count or stable source snapshot identifier when available

Capture after guarded reindex:

- `mutation_executor.selection_state=guarded_live_executor`
- `mutation_executor.actual_runtime_handler=index_service.reindex`
- `mutation_executor_result.runtime_chunks`
- `mutation_executor_result.runtime_vectors`
- `mutation_executor_audit_receipt.record_kind=mutation_executor_post_execution`
- `mutation_executor_audit_receipt.pre_executor_audit_sequence_id`
- top-level promotion state if the promotion command was used

Capture after recovery rebuild:

- recovery action result from source-document rebuild
- recovered vector count
- health check status
- audit record or local drill log linking the recovery action to the failed/suspect guarded run

## Drill Flow

1. Run default smoke.
2. Capture pre-state for the target collection.
3. Run guarded top-level promotion smoke with local audit enabled.
4. Confirm pre/post audit sequence linkage.
5. Run recovery rebuild from source documents for the same collection.
6. Capture post-recovery state.
7. Compare pre-state, guarded result, and post-recovery state.
8. Mark the drill passed only if the recovered collection is queryable and vector counts are internally consistent.

## Pass Criteria

- All commands are local-only.
- Pre/post executor audit sequence linkage is present.
- Guarded reindex returns non-zero chunks and vectors.
- Recovery rebuild completes without exception.
- Recovered vector count is non-zero.
- Health check remains `ok`.
- No upload review path is invoked.
- No public/external surface is required.

## Abort Conditions

- audit backend is not `local_file_append_only`
- post-executor audit receipt is missing
- pre/post audit sequence linkage is missing
- source documents are unavailable
- recovery rebuild raises an exception
- recovered vector count is zero
- health check fails after recovery
- operator cannot confirm the target collection is safe local runtime data

## Next Implementation Scope

`LOOP-078 V1.5 reindex live adapter rollback drill harness draft` should add a small local-only script or smoke mode that:

- captures pre-state,
- runs guarded top-level promotion,
- runs rebuild-from-source recovery,
- emits a compact drill report,
- refuses to run without explicit local audit and mutation execution env vars.

## Verification

- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`

