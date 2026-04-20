# V1.5 Reindex Live Adapter Executor Injection Protocol Draft (2026-04-20)

## 목적
- future `reindex` live adapter의 explicit local-only binding이 어떤 carrier를 따라 runtime/test harness에서 executor selection 단계까지 전달되는지 고정한다.

## Carrier Chain
- `services/agent_runtime_service.py`
  - `AgentRuntimeRequest.executor_binding`
- `services/tool_registry_service.py`
  - `ToolContext.executor_binding`
- `services/mutation_executor_service.py`
  - `MutationExecutionRequest.executor_binding`

## Protocol Guardrails
- binding은 payload channel로 받지 않는다.
- binding owner는 `local_runtime_or_test_harness`로 제한한다.
- binding이 없어도 기본 경로는 계속 `candidate_stub` 또는 `noop_fallback`이다.
- activation guard와 durable audit guard가 binding보다 먼저 평가된다.

## Contract Signals
- `mutation_executor.request.executor_binding_present`
- `mutation_executor.request.executor_binding_kind`
- `mutation_executor.request.executor_binding_source`
- `mutation_executor.request.executor_binding_executor_name`

## 현재 코드 반영
- `boundary.live_adapter_outline.executor_injection_protocol`
  - carrier chain, direct entrypoint, default behavior, required guards를 코드 계약으로 고정했다.
- `agent_runtime_service.run_agent_entry()`
  - request-scoped binding을 `ToolContext`로 전달한다.
- `tool_middleware_service._build_mutation_execution_request()`
  - context binding을 mutation execution request에 그대로 전달한다.

## 비목표
- public `/agent/*` surface
- upload review binding
- actual live execution enablement

## 검증
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
