# V1.5 reindex live adapter guarded top-level promotion gate draft

Date: 2026-04-22
Loop: `LOOP-073`

## Decision

`Go` for post-promotion enablement checkpoint review.

Explicit local-only guarded top-level promotion now works behind an extra opt-in. Default/public behavior remains blocked.

## Implementation

1. `services/mutation_executor_service.py`
   - Added the explicit top-level promotion binding field constants.

2. `services/tool_middleware_service.py`
   - Added guarded top-level promotion helpers.
   - Requires all of the following before promotion:
     - `guarded_live_executor` selection
     - explicit top-level promotion opt-in in `executor_binding`
     - executor success or eligible executor failure sidecar
     - linked `mutation_executor_post_execution` audit receipt
   - Promotes success to top-level `ok=true` with the existing reindex result schema.
   - Promotes eligible failure to top-level reindex adapter error schema.
   - Keeps executor sidecars, audit receipt, and promotion router evidence in `execution_trace.contracts`.

3. `scripts/smoke_agent_runtime.py`
   - Added `DOC_RAG_MUTATION_SMOKE_TOP_LEVEL_PROMOTION=1`.
   - Added `--opt-in-top-level-promotion`.
   - Smoke validation now accepts top-level success only for the explicit guarded promotion path.

4. Tests
   - Middleware success and failure promotion tests.
   - Agent runtime explicit opt-in success test.
   - Smoke harness top-level promotion opt-in test.
   - Existing default guarded path still asserts `MUTATION_APPLY_NOT_ENABLED`.

## Live Evidence

Guarded top-level promotion smoke command:

```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 \
  DOC_RAG_MUTATION_AUDIT_BACKEND=local_file \
  DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag-guarded-top-level-smoke \
  ./.venv/bin/python scripts/smoke_agent_runtime.py \
  --opt-in-live-binding \
  --opt-in-live-binding-stage-guarded \
  --opt-in-top-level-promotion
```

Observed output:

- `ok=true`
- requested live binding stage: `guarded_live_executor`
- requested top-level promotion: `true`
- apply summary `ok=true`
- apply error code: `null`
- pre-executor audit sequence id: `6`
- post-executor audit sequence id: `7`
- post-executor record kind: `mutation_executor_post_execution`
- top-level promotion router state: `enabled_explicit_local_only`
- top-level promotion enabled: `true`
- runtime chunks: `37`
- runtime vectors: `37`

Audit tail confirmed the durable post-executor record:

- `record.source_schema_version=v1.5.mutation_executor_post_execution_audit.v1`
- `record.outcome.ok=true`
- `record.audit.events[0].pre_executor_audit_sequence_id=6`
- `record.mutation_executor_audit.result.runtime_chunks=37`
- `record.mutation_executor_audit.result.runtime_vectors=37`
- `sequence_id=7`

## Verification

- `./.venv/bin/python -m pytest -q tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py tests/test_mutation_executor_service.py` -> `64 passed`
- guarded top-level promotion smoke command above -> `ok=true`

## Remaining Gate

Default/public top-level promotion remains `No-Go`. The next checkpoint must decide whether to keep this extra opt-in as the final local-only operator surface, add runbook coverage, or require rollback drill evidence before any broader enablement.

