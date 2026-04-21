# V1.5 Reindex Live Adapter Failure Taxonomy Draft - 2026-04-21

## Summary

`reindex` live adapter의 adapter-specific runtime failure taxonomy를 호출 가능한 contract helper와 테스트 seam으로 고정했다. actual live execution은 계속 닫혀 있으므로 이 failure surface는 현재 top-level runtime에서 방출되지 않는다.

## Failure Contracts

schema:
- `v1.5.reindex_live_adapter_error.v1`

codes:

1. `REINDEX_TARGET_MISMATCH`
   - stage: `contract_validation`
   - retryable: `false`
   - trigger: `payload_apply_preview_target_mismatch`
2. `REINDEX_AUDIT_LINKAGE_INVALID`
   - stage: `audit_linkage`
   - retryable: `false`
   - trigger: `append_only_receipt_unlinkable`
3. `REINDEX_RUNTIME_EXECUTION_FAILED`
   - stage: `executor_runtime`
   - retryable: `true`
   - trigger: `reindex_runtime_failed`
4. `REINDEX_ROLLBACK_HINT_UNAVAILABLE`
   - stage: `post_execution`
   - retryable: `true`
   - trigger: `operator_restore_hint_missing`

## Surface Mapping

현재 surface:

- kind: `draft_only_not_runtime_reachable`
- top-level `ok=false`
- top-level `error.code=MUTATION_APPLY_NOT_ENABLED`
- blocked middleware: `mutation_apply_guard`

future failure surface:

- kind: `top_level_apply_failure`
- top-level `ok=false`
- error location: `error`
- retained contracts: `mutation_executor`, `mutation_failure_taxonomy`

## What Changed

1. `services/mutation_executor_service.py`
   - `REINDEX_ERROR_*` constants와 ordered taxonomy metadata를 추가했다.
   - `build_reindex_live_failure_contract()`를 추가해 개별 failure code를 current/future surface mapping과 함께 반환한다.
   - `list_reindex_live_failure_contracts()`를 추가해 네 failure code 순서를 테스트 가능한 seam으로 고정했다.
   - `boundary.live_adapter_outline.failure_taxonomy`가 같은 ordered metadata helper를 사용하게 했다.
2. `tests/test_mutation_executor_service.py`
   - 네 failure code의 stage/retryable 순서, future failure surface mapping, detail preservation, unknown code rejection, boundary taxonomy alignment를 검증한다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py` -> `14 passed in 0.07s`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py` -> `53 passed in 0.10s`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready` (`active_id=LOOP-057`)
- `git diff --check` -> pass

## Follow-up

다음 단계는 actual execution enablement를 바로 여는 것이 아니라, `reindex` 단일 tool에 대해 어떤 조건에서 `mutation_apply_guard_execution_enabled`를 열 수 있는지 go/no-go로 재검토하는 것이다.
