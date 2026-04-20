# V1.5 Reindex Live Adapter Concrete Smoke Evidence Draft - 2026-04-21

## Summary

`scripts/smoke_agent_runtime.py`에 concrete executor skeleton stage opt-in을 추가했고, local activation + durable local audit + explicit live binding 조합에서 `live_result_skeleton` evidence를 실제 smoke output으로 확인했다.

## Command Surface

- CLI: `./.venv/bin/python scripts/smoke_agent_runtime.py --opt-in-live-binding --opt-in-live-binding-stage-concrete`
- Env: `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING=1`
- Optional stage override env: `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING_STAGE=concrete_executor_skeleton`

## Observed Evidence

실측 명령:

```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 \
  DOC_RAG_MUTATION_AUDIT_BACKEND=local_file \
  DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag-live-binding-concrete-smoke \
  ./.venv/bin/python scripts/smoke_agent_runtime.py \
  --opt-in-live-binding \
  --opt-in-live-binding-stage-concrete
```

확인된 핵심 값:

- `ok=true`
- `requested_live_binding=true`
- `requested_live_binding_stage=concrete_executor_skeleton`
- `checks[].summary.mutation_executor.executor_name=reindex_mutation_adapter_live`
- `checks[].summary.mutation_executor.selection_state=live_result_skeleton`
- `checks[].summary.mutation_executor_result.schema_version=v1.5.reindex_live_adapter_result.v1`
- `checks[].summary.mutation_executor_result.operation=rebuild_vector_index`
- `checks[].summary.mutation_executor_result.requested_compatibility_bundle=true`

## Testing

- `./.venv/bin/python -m pytest -q tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`

## Follow-up

현재 smoke는 여전히 blocked-success evidence다. 다음 단계는 `mutation_executor_result` sidecar와 future top-level apply success 응답 사이의 promotion rule을 문서/contract로 고정하는 것이다.
