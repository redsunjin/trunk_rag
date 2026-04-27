# V1.5 Reindex Live Adapter Opt-In Smoke Evidence Draft (2026-04-20)

## 실행 명령
```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 \
  DOC_RAG_MUTATION_AUDIT_BACKEND=local_file \
  DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag-live-binding-smoke \
  ./.venv/bin/python scripts/smoke_agent_runtime.py --opt-in-live-binding
```

## 관찰 결과
- top-level
  - `ok=true`
  - `requested_live_binding=true`
- apply check
  - `name=write_tool_apply_not_enabled`
  - `error_code=MUTATION_APPLY_NOT_ENABLED`
  - `mutation_executor.executor_name=reindex_mutation_adapter_live`
  - `mutation_executor.selection_state=live_binding_stub`
  - `mutation_executor.selection_reason=explicit_live_binding_requested`
  - `mutation_executor.activation_requested=true`
  - `mutation_executor.audit_sink_type=local_file_append_only`
  - `mutation_executor.audit_sequence_id=6`
- audit receipt
  - `storage_path=/tmp/trunk_rag-live-binding-smoke/audit-20260420.jsonl`
  - `retention_days=90`
  - `prune_policy=rolling_window`

## 해석
- opt-in smoke command는 default blocked smoke를 깨지 않고 live binding stub selection evidence를 별도 경로에서 재현한다.
- 실제 live execution은 여전히 열리지 않았고, smoke의 성공 조건은 structured blocked/live-stub contract evidence가 유지되는지 여부다.

## 참고
- JSON 출력 전에 telemetry warning 두 줄이 찍혔지만 smoke 결과 자체는 `ok=true`로 완료됐다.
