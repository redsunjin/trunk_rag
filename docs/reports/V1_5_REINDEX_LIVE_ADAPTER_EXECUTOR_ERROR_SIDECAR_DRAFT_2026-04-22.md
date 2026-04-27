# V1.5 reindex live adapter executor error sidecar draft

Date: 2026-04-22
Loop: `LOOP-069`

## Decision

`Go` for post-error-sidecar enablement checkpoint review.

The blocked apply surface now carries deterministic executor failure evidence when the guarded executor is invoked but does not produce a result.

## Implementation

1. `services/tool_middleware_service.py`
   - Added `ToolExecutionState.mutation_executor_error`.
   - Captures `execute_mutation_request(...).error` when the mutation executor returns `ok=false`.
   - Attaches `mutation_executor_error` to blocked apply `error` and `execution_trace.contracts`.
   - Passes executor error to the top-level promotion router.

2. `services/mutation_executor_service.py`
   - `build_reindex_top_level_promotion_router_contract(...)` accepts `executor_error`.
   - Failure route becomes eligible when the executor error code is in the reindex live adapter failure taxonomy.
   - Adds `failure_error_preview` with schema version, code, message, and exception type.
   - Keeps promotion gates disabled.

3. `scripts/smoke_agent_runtime.py`
   - Smoke summary now includes `mutation_executor_error`.
   - Top-level promotion router summary exposes failure route eligibility/error code when present.

## Expected Failure Evidence

When a guarded executor failure occurs:

- top-level response still has `error.code=MUTATION_APPLY_NOT_ENABLED`
- `error.mutation_executor.selection_state=guarded_live_executor`
- `error.mutation_executor.actual_runtime_handler_invoked=true`
- `error.mutation_executor_error.code=REINDEX_RUNTIME_EXECUTION_FAILED`
- `execution_trace.contracts.mutation_executor_error` matches the blocked apply sidecar
- `error.mutation_top_level_promotion_router.failure_route.eligible=true`
- `error.mutation_top_level_promotion_router.failure_route.error_code=REINDEX_RUNTIME_EXECUTION_FAILED`
- `error.mutation_top_level_promotion_router.failure_error_preview` mirrors the executor error

## Verification

- `./.venv/bin/python -m pytest -q tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py tests/test_mutation_executor_service.py` -> `46 passed`

## Remaining Gate

Success and failure sidecars are now both visible on the blocked apply surface. Top-level apply success/failure promotion still remains disabled until the next enablement checkpoint reviews whether durable post-executor audit evidence or rollback drill evidence is required before opening the gate.
