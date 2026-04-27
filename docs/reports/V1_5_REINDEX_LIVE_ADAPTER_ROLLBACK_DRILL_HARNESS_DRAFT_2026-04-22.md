# V1.5 reindex live adapter rollback drill harness draft

Date: 2026-04-22
Loop: `LOOP-078`

## Decision

`Go` for rollback drill execution evidence.

The local-only rollback drill now has a harness that refuses to run unless explicit local mutation and local-file audit env vars are present.

## Implementation

1. `scripts/smoke_reindex_rollback_drill.py`
   - Adds `v1.5.reindex_live_adapter_rollback_drill.v1` report schema.
   - Refuses to run without:
     - `DOC_RAG_AGENT_MUTATION_EXECUTION=1`
     - `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file`
     - `DOC_RAG_MUTATION_AUDIT_DIR=<local path>`
   - Captures pre-state vector count for the target collection.
   - Runs guarded top-level promotion smoke through `scripts.smoke_agent_runtime.run_smoke()`.
   - Verifies `mutation_executor_post_execution` audit linkage from apply pre-executor sequence to post-executor sequence.
   - Runs rebuild-from-source recovery via `index_service.reindex(reset=True)`.
   - Captures post-recovery vector count and emits a compact structured report.

2. `tests/test_smoke_reindex_rollback_drill.py`
   - Verifies env guard refusal without side effects.
   - Verifies guarded promotion and recovery orchestration using monkeypatched smoke/reindex calls.

## Verification

- `./.venv/bin/python -m pytest -q tests/test_smoke_reindex_rollback_drill.py` -> `2 passed`

## Next Step

Run the harness with explicit local env and capture rollback drill execution evidence. This remains local-only and does not open default/public promotion.

