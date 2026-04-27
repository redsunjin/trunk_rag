# V1.5 Reindex Live Adapter Pre-Execution Handoff Seam Draft - 2026-04-21

## Summary

`reindex` live adapter actual side effect를 열지 않고, future execution이 반드시 지나야 할 pre-execution handoff seam을 contract helper로 고정했다. 이 seam은 durable audit receipt, mutation executor router, explicit live adapter binding, top-level success/failure promotion이 side effect 이전에 한 흐름으로 묶여야 한다는 조건을 테스트 가능한 형태로 남긴다.

## What Changed

1. `services/mutation_executor_service.py`
   - `v1.5.reindex_live_adapter_pre_execution_handoff.v1` schema constant를 추가했다.
   - `build_reindex_pre_execution_handoff_contract()`를 추가했다.
2. `tests/test_mutation_executor_service.py`
   - pre-execution handoff contract가 direct tool handler 우회 차단, durable audit receipt precondition, explicit binding, promotion handoff, blocked-until 조건을 모두 고정하는지 검증한다.

## Contract Highlights

현재 runtime:

- valid apply envelope 이후에도 `mutation_apply_guard`는 `MUTATION_APPLY_NOT_ENABLED`를 반환한다.
- mutation executor invocation은 blocked result metadata enrichment 경로에만 붙는다.
- guard를 단순히 열면 direct tool handler가 호출될 수 있으므로 actual execution은 아직 닫혀 있다.

required pre-execution order:

1. `validate_apply_envelope`
2. `build_persisted_audit_record`
3. `append_durable_audit_receipt`
4. `build_mutation_execution_request`
5. `resolve_mutation_executor`
6. `execute_mutation_executor`
7. `promote_executor_result_or_error`

side-effect barrier:

- `actual_reindex_side_effect_allowed=false`
- direct tool handler: `tool_registry_service._tool_reindex`
- actual runtime handler: `index_service.reindex`
- required router before side effect: `mutation_executor_service.execute_mutation_request`

## Remaining Before Enablement

1. `mutation_apply_guard`가 direct tool handler 대신 executor router로 넘기는 runtime path
2. side effect 이전 durable audit receipt 생성/검증
3. explicit live adapter binding precondition enforcement
4. top-level success/failure promotion router
5. fake/sandboxed executor smoke

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py` -> `15 passed in 0.07s`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py` -> `50 passed in 0.09s`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`
- `git diff --check` -> pass

## Follow-up

다음 단계는 actual `index_service.reindex()` side effect를 열지 않고 fake/sandboxed executor smoke seam을 추가해, future runtime router가 실제 index mutation 없이 success/failure promotion을 검증할 수 있게 하는 것이다.
