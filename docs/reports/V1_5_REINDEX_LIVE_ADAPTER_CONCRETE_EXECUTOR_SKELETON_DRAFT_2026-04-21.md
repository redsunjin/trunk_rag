# V1.5 Reindex Live Adapter Concrete Executor Skeleton Draft - 2026-04-21

## Summary

`reindex` live adapter의 explicit binding path에 `concrete_executor_skeleton` stage를 추가했다. 이 stage는 실제 side effect를 열지 않은 채 future live execution의 result shape를 `mutation_executor_result` sidecar로 고정한다.

## What Changed

1. `services/mutation_executor_service.py`
   - `binding_stage` field와 `selection_stub` / `concrete_executor_skeleton` stage constant를 추가했다.
   - valid explicit live binding이 `concrete_executor_skeleton` stage를 요청하면 `ReindexLiveMutationExecutorSkeleton`을 선택하도록 확장했다.
   - skeleton executor는 `reindex_summary`, `audit_receipt_ref`, `rollback_hint`를 포함한 `v1.5.reindex_live_adapter_result.v1` payload를 반환한다.
2. `services/tool_middleware_service.py`
   - `MUTATION_APPLY_NOT_ENABLED` error path에서 executor contract 외에 `mutation_executor_result` sidecar도 함께 trace/error contract에 남기도록 확장했다.
3. `services/agent_runtime_service.py`
   - runtime entry 결과에서도 `mutation_executor_result` sidecar가 유지되도록 integration coverage를 보강했다.

## Result Contract

- `selection_state`: `live_result_skeleton`
- `selection_reason`: `explicit_live_result_contract_requested`
- `executor.execution_enabled`: `true`
- `mutation_executor_result.schema_version`: `v1.5.reindex_live_adapter_result.v1`
- `reindex_summary.operation`: `rebuild_vector_index`
- `rollback_hint.mode`: `rebuild_from_source_documents`

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`

## Follow-up

다음 단계는 이 sidecar result를 future top-level apply success surface로 어떻게 승격할지 handoff 규칙을 정리하는 것이다. actual execution은 계속 off-by-default로 유지한다.
