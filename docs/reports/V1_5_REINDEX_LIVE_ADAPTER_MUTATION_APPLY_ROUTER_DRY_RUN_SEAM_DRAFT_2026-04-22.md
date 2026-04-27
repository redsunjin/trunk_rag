# V1.5 Reindex Live Adapter Mutation Apply Router Dry-Run Seam Draft - 2026-04-22

## Summary

`reindex` live adapter actual side effect를 열지 않고, preview-confirmed apply가 direct tool handler로 빠지지 않아야 한다는 mutation apply executor router dry-run seam을 contract helper와 middleware evidence로 고정했다. 이 seam은 current blocked apply path에서 `mutation_executor_service.execute_mutation_request`를 dry-run으로 호출하되, `tool_registry_service._tool_reindex`와 `index_service.reindex`는 호출하지 않는다는 기준을 남긴다.

## What Changed

1. `services/mutation_executor_service.py`
   - `v1.5.reindex_live_adapter_mutation_apply_router_dry_run.v1` schema constant를 추가했다.
   - `build_reindex_mutation_apply_router_dry_run_contract()`를 추가했다.
   - dry-run contract가 pre-execution handoff contract와 fake executor smoke contract를 같은 router 기준으로 연결한다.
2. `services/tool_middleware_service.py`
   - `MUTATION_APPLY_NOT_ENABLED` blocked apply metadata에 `mutation_apply_router_dry_run` contract를 추가했다.
   - contract를 error payload와 `execution_trace.contracts`에 함께 남긴다.
3. `tests/test_mutation_executor_service.py`, `tests/test_tool_middleware_service.py`
   - dry-run contract shape와 middleware evidence를 검증한다.
   - direct reindex tool handler가 apply dry-run 중 호출되지 않는 것을 monkeypatch로 고정했다.

## Contract Highlights

apply guard:

- validated apply envelope: `true`
- blocked error code: `MUTATION_APPLY_NOT_ENABLED`
- blocked before tool handler: `true`

router handoff:

- route location: `blocked_result_metadata_enrichment`
- request builder: `tool_middleware_service._build_mutation_execution_request`
- router: `mutation_executor_service.execute_mutation_request`
- direct tool handler invoked: `false`
- actual runtime handler invoked: `false`

linked contracts:

- pre-execution handoff schema: `v1.5.reindex_live_adapter_pre_execution_handoff.v1`
- fake smoke schema: `v1.5.reindex_live_adapter_fake_executor_smoke.v1`

## Remaining Before Enablement

1. actual execution enablement checkpoint review
2. `mutation_apply_guard_execution_enabled` 구현 여부 판단
3. side effect 이전 durable audit receipt 생성 위치 최종 고정
4. top-level success/failure promotion router 구현 여부 판단
5. real side-effect rollback drill 여부 판단

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py` -> `34 passed in 0.13s`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py` -> `52 passed in 0.10s`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`
- `git diff --check` -> pass

## Follow-up

다음 단계는 actual `index_service.reindex()` side effect를 열기 전에 enablement checkpoint review를 다시 수행해, dry-run seam 이후에도 남은 blocker와 Go/No-Go 조건을 재판정하는 것이다.
