# V1.5 Mutation Executor Interface Draft - 2026-04-18

## Scope

- 대상 루프: `LOOP-035 V1.5 mutation executor interface draft`
- 기준 상태: `LOOP-034` go/no-go review 반영 이후
- 목적: 실제 write execution을 열지 않은 상태에서 mutation executor protocol, noop/default executor, tool adapter registry seam을 코드/테스트/문서 기준으로 고정한다.

## Decision

- live write execution은 여전히 열지 않는다.
- `services/mutation_executor_service.py`를 추가해 preview-confirmed apply 이후 단계가 기대할 executor request/contract를 분리한다.
- 기본 executor는 `NoopMutationExecutor`로 유지한다.
- 첫 tool-specific seam은 `reindex`에 대해서만 `ReindexMutationExecutorAdapter` stub를 둔다.
- `approve_upload_request`, `reject_upload_request`는 아직 tool-specific executor를 등록하지 않고 default noop로 남긴다.

## Executor Interface

핵심 구성은 아래와 같다.

- `MutationExecutionRequest`
  - `request_id`
  - `tool_name`
  - `payload`
  - `apply_envelope`
  - `preview_seed`
  - `persisted_audit_record`
  - `audit_sink_receipt`
  - `actor`, `actor_category`
  - `allow_mutation`
  - `timeout_seconds`
- `MutationExecutor` protocol
  - `supports(tool_name)`
  - `execute(request)`
- `NoopMutationExecutor`
  - 기본 fallback executor
  - 항상 `MUTATION_APPLY_NOT_ENABLED`를 반환한다.
- `ReindexMutationExecutorAdapter`
  - `reindex` 전용 stub adapter
  - 실제 reindex를 실행하지 않고, tool-specific binding seam만 고정한다.

## Executor Contract

executor 결과는 아래 contract를 포함한다.

```json
{
  "schema_version": "v1.5.mutation_executor_contract.v1",
  "executor_name": "reindex_mutation_adapter_stub",
  "binding_kind": "tool_adapter_stub",
  "tool_name": "reindex",
  "tool_registered": true,
  "activation_requested": false,
  "execution_enabled": false,
  "delegate_executor_name": "noop_mutation_executor",
  "request": {
    "request_id": "req-123",
    "actor_category": "maintenance_mutation",
    "allow_mutation": true,
    "timeout_seconds": 30.0,
    "apply_schema_version": "v1.5.mutation_apply_envelope.v1",
    "preview_schema_version": "v1.5.mutation_preview_seed.v1",
    "audit_record_schema_version": "v1.5.mutation_audit_record.v1",
    "audit_sink_type": "null_append_only"
  }
}
```

고정 규칙:

- `execution_enabled`는 이번 단계에서도 항상 `false`다.
- `activation_requested`는 `DOC_RAG_AGENT_MUTATION_EXECUTION` env seam만 반영하고 live execution을 보장하지 않는다.
- `tool_registered=true`는 live adapter가 아니라 tool-specific stub binding이 존재한다는 뜻이다.

## Runtime Integration

- `services/tool_middleware_service.py`
  - valid `apply_envelope`가 `mutation_apply_guard`를 통과해도 기존처럼 `MUTATION_APPLY_NOT_ENABLED`로 차단한다.
  - 대신 middleware metadata / execution trace contract에 `mutation_executor` contract를 추가한다.
- `tests/test_tool_middleware_service.py`
  - valid `reindex` apply가 tool-specific stub contract를 남기는지 검증한다.
- `tests/test_agent_runtime_service.py`
  - agent runtime entry가 `mutation_executor` contract를 error/execution trace에 함께 남기는지 검증한다.
- `tests/test_mutation_executor_service.py`
  - `reindex` stub binding과 default noop fallback을 직접 검증한다.

## Non-goals

- 실제 `reindex` 실행 연결
- upload review live executor 추가
- public `/agent/*` endpoint
- durable audit backend 구현

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_tool_trace_service.py tests/test_tool_preview_service.py tests/test_tool_audit_sink_service.py tests/test_tool_apply_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-036 V1.5 durable mutation audit backend skeleton`이다. 이 단계에서는 default sink를 그대로 보수적으로 유지하면서, explicit local config로만 선택되는 append-only file backend skeleton과 stable `sequence_id` seam을 추가한다.
