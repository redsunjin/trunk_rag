# V1.5 Reindex Live Adapter Success Promotion Draft - 2026-04-21

## Summary

`reindex` live adapter concrete skeleton의 `mutation_executor_result` sidecar를 future top-level apply success surface로 승격할 때의 handoff rule을 계약으로 고정했다. 현재 runtime은 계속 `MUTATION_APPLY_NOT_ENABLED` blocked-success surface를 유지하고, actual side effect는 열지 않는다.

## What Changed

1. `services/mutation_executor_service.py`
   - `v1.5.reindex_live_adapter_success_promotion.v1` schema constant를 추가했다.
   - `build_reindex_live_success_promotion_contract()`를 추가해 `live_result_skeleton` executor contract와 `v1.5.reindex_live_adapter_result.v1` sidecar를 future success surface로 매핑한다.
2. `services/tool_middleware_service.py`
   - concrete skeleton path에서 `mutation_success_promotion` contract를 error payload와 execution trace contracts에 함께 남긴다.
   - current top-level 응답은 여전히 `ok=false`, `error.code=MUTATION_APPLY_NOT_ENABLED`다.
3. `scripts/smoke_agent_runtime.py`
   - concrete opt-in smoke summary가 `mutation_success_promotion` evidence를 요약할 수 있게 했다.

## Promotion Rule

현재 surface:

- top-level `ok=false`
- top-level `error.code=MUTATION_APPLY_NOT_ENABLED`
- result payload 위치: `error.mutation_executor_result`
- retained trace 위치: `execution_trace.contracts.mutation_executor_result`
- blocked middleware: `mutation_apply_guard`

future success surface:

- top-level `ok=true`
- top-level `error=null`
- result payload 위치: `result`
- promoted fields: `reindex_summary`, `audit_receipt_ref`, `rollback_hint`
- retained contracts: `mutation_executor`, `mutation_executor_result`, `mutation_success_promotion`

승격 gate는 아직 닫혀 있다. `promotion_gate.actual_side_effect_enabled=false`이며, 실제 전환에는 `mutation_apply_guard_execution_enabled`, `executor_result_ok`, `live_result_skeleton`, `durable_audit_ready`, `explicit_live_adapter_binding` 신호가 함께 필요하다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py` -> `46 passed in 0.17s`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py` -> `50 passed in 0.10s`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready` (`active_id=LOOP-056`)
- `git diff --check` -> pass

## Follow-up

다음 단계는 adapter-specific runtime failure taxonomy deep cases를 테스트 seam으로 고정하는 것이다. 기본 smoke와 public surface는 계속 현행 blocked path를 유지한다.
