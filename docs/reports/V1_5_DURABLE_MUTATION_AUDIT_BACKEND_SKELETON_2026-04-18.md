# V1.5 Durable Mutation Audit Backend Skeleton - 2026-04-18

## Scope

- 대상 루프: `LOOP-036 V1.5 durable mutation audit backend skeleton`
- 기준 상태: `LOOP-035` mutation executor interface draft 반영 이후
- 목적: default sink는 그대로 보수적으로 유지하면서, explicit local config로만 선택되는 append-only file audit backend skeleton과 stable `sequence_id` seam을 고정한다.

## Decision

- 기본 backend는 계속 `null_append_only`다.
- `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file`일 때만 local append-only file sink를 사용한다.
- local file sink는 `chroma_db/mutation_audit/`를 기본 루트로 사용하고, `DOC_RAG_MUTATION_AUDIT_DIR`로 override할 수 있다.
- retention 정책은 `90일 rolling_window`, rotation 단위는 `day`로 먼저 고정한다.
- prune job 자동화는 이번 단계 범위 밖이다. 대신 receipt와 stored entry에 retention/rotation metadata만 남긴다.

## Backend Shape

- `services/tool_audit_sink_service.py`
  - `LocalFileAppendOnlyAuditSink`
  - `resolve_append_only_audit_sink()`
  - `get_configured_append_only_audit_sink()`
  - env key:
    - `DOC_RAG_MUTATION_AUDIT_BACKEND`
    - `DOC_RAG_MUTATION_AUDIT_DIR`

local file entry 예시:

```json
{
  "sequence_id": 1,
  "written_at": "2026-04-18T09:00:00+00:00",
  "rotation_unit": "day",
  "prune_policy": "rolling_window",
  "retention_days": 90,
  "record": {
    "schema_version": "v1.5.mutation_audit_record.v1"
  }
}
```

receipt 예시:

```json
{
  "accepted": true,
  "sink_type": "local_file_append_only",
  "record_schema_version": "v1.5.mutation_audit_record.v1",
  "sequence_id": 1,
  "storage_path": "/.../chroma_db/mutation_audit/audit-20260418.jsonl",
  "rotation_unit": "day",
  "prune_policy": "rolling_window",
  "retention_days": 90
}
```

## Stable Sequence Id Rule

- `sequence_state.json`에 `last_sequence_id`를 저장한다.
- 다음 append 시 이 값을 1 증가시켜 stable `sequence_id`를 발급한다.
- process 재시작 뒤에도 같은 root dir를 사용하면 sequence는 이어진다.

## Validation

- `tests/test_tool_audit_sink_service.py`
  - memory sink 유지
  - local file sink의 `sequence_id`, receipt metadata, persisted entry 확인
  - env-configured backend selection 확인
- broader target:
  - `./.venv/bin/python -m pytest -q tests/test_tool_audit_sink_service.py tests/test_mutation_executor_service.py tests/test_tool_trace_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
  - `./.venv/bin/python scripts/roadmap_harness.py validate`

## Non-goals

- durable backend를 기본값으로 승격
- prune scheduler 구현
- live mutation execution 개방
- upload review executor 연결

## Next Step

다음 loop는 `LOOP-037 V1.5 reindex executor activation seam draft`다. 이 단계에서는 `DOC_RAG_AGENT_MUTATION_EXECUTION`, durable audit backend readiness, `reindex` stub binding 사이의 activation guard를 한 군데로 모은다.
