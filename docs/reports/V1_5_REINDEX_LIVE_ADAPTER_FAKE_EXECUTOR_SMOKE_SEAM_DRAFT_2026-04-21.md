# V1.5 Reindex Live Adapter Fake Executor Smoke Seam Draft - 2026-04-21

## Summary

`reindex` live adapter actual side effect를 열지 않고, future runtime router가 success/failure promotion을 검증할 수 있는 fake/sandboxed executor smoke seam을 contract helper로 고정했다. 이 seam은 pre-execution handoff contract를 참조하면서도 `index_service.reindex()`를 호출하지 않는 smoke evidence 기준만 남긴다.

## What Changed

1. `services/mutation_executor_service.py`
   - `v1.5.reindex_live_adapter_fake_executor_smoke.v1` schema constant를 추가했다.
   - fake success/failure selection state constant를 추가했다.
   - `build_reindex_fake_executor_smoke_contract()`를 추가했다.
   - success promotion contract가 sandboxed success selection state도 smoke evidence로 매핑할 수 있게 했다.
2. `tests/test_mutation_executor_service.py`
   - fake smoke contract가 pre-execution handoff, side-effect policy, success promotion evidence, failure surface evidence, smoke summary field contract를 함께 고정하는지 검증한다.

## Contract Highlights

side-effect policy:

- `actual_reindex_side_effect_allowed=false`
- `calls_index_service_reindex=false`
- `sandboxed_executor_only=true`
- `public_surface_allowed=false`

success smoke evidence:

- selection state: `fake_executor_smoke_success`
- result schema: `v1.5.reindex_live_adapter_result.v1`
- promotion schema: `v1.5.reindex_live_adapter_success_promotion.v1`
- current surface: `blocked_success_sidecar`
- future surface: `top_level_apply_success`

failure smoke evidence:

- selection state: `fake_executor_smoke_failure`
- error schema: `v1.5.reindex_live_adapter_error.v1`
- representative failure code: `REINDEX_RUNTIME_EXECUTION_FAILED`
- future surface: `top_level_apply_failure`

## Remaining Before Enablement

1. fake success/failure smoke command or runtime path
2. `mutation_apply_guard`가 direct tool handler 대신 executor router로 넘기는 dry-run path
3. top-level success/failure promotion router
4. explicit live adapter binding enforcement before side effect
5. actual execution go/no-go 재검토

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py` -> `16 passed in 0.07s`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py` -> `51 passed in 0.09s`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`
- `git diff --check` -> pass

## Follow-up

다음 단계는 actual `index_service.reindex()` side effect를 열지 않고 `mutation_apply_guard` 이후 write path가 mutation executor router dry-run으로 빠지는 조건을 고정하는 것이다.
