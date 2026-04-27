# V1.5 reindex live adapter guarded live executor smoke command draft

Date: 2026-04-22
Loop: `LOOP-066`

## Decision

`Go` for a separate guarded live executor smoke evidence loop.

The default smoke path remains side-effect-free. The concrete skeleton smoke path also remains side-effect-free. Actual `index_service.reindex()` invocation is reachable only through explicit local-only live binding plus the guarded stage selector.

## Command Surface

- Default blocked smoke: `./.venv/bin/python scripts/smoke_agent_runtime.py`
- Side-effect-free live binding smoke: `./.venv/bin/python scripts/smoke_agent_runtime.py --opt-in-live-binding`
- Side-effect-free concrete result skeleton smoke: `./.venv/bin/python scripts/smoke_agent_runtime.py --opt-in-live-binding --opt-in-live-binding-stage-concrete`
- Guarded live executor smoke command: `./.venv/bin/python scripts/smoke_agent_runtime.py --opt-in-live-binding --opt-in-live-binding-stage-guarded`
- Env live binding opt-in: `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING=1`
- Env stage override: `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING_STAGE=guarded_live_executor`

The smoke CLI rejects simultaneous concrete and guarded stage flags, so a single command cannot silently select both side-effect-free concrete evidence and guarded runtime execution.

## Evidence Contract

The guarded command injects this executor binding into the apply request:

```json
{
  "binding_kind": "reindex_live_adapter",
  "binding_source": "smoke_harness",
  "executor_name": "reindex_mutation_adapter_live",
  "binding_stage": "guarded_live_executor"
}
```

When the guarded executor result is present, smoke summary output can expose:

- `mutation_executor.selection_state=guarded_live_executor`
- `mutation_executor.actual_runtime_handler=index_service.reindex`
- `mutation_executor.actual_runtime_handler_invoked=true`
- `mutation_executor_result.runtime_chunks`
- `mutation_executor_result.runtime_vectors`
- `mutation_executor_result.runtime_scope`
- `mutation_executor_result.runtime_collection`
- `mutation_executor_result.runtime_reindex_scope`

## Guardrails

- No public route is enabled.
- Default smoke does not send live binding.
- Concrete skeleton smoke still selects `live_result_skeleton` and does not call `index_service.reindex()`.
- Current top-level apply response remains the blocked `MUTATION_APPLY_NOT_ENABLED` surface until a later promotion gate is explicitly opened.
- The guarded command is local-only and should be run with explicit mutation activation plus durable local audit config.

## Verification

- `./.venv/bin/python -m pytest -q tests/test_smoke_agent_runtime.py tests/test_mutation_executor_service.py` -> `24 passed`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready` (`LOOP-067` active)
- `git diff --check` -> passed

## Next Step

`LOOP-067 V1.5 reindex live adapter guarded live executor smoke evidence draft` should run the guarded command with local file audit enabled and capture the blocked top-level surface plus runtime sidecar evidence.
