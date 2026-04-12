# V1.5 Preview Seed And Audit Sink Skeleton - 2026-04-12

## Scope

- 대상 루프: `LOOP-031 V1.5 preview seed + audit sink skeleton`
- 기준 커밋: `5eae38a feat(agent): define preview audit contract`
- 목적: `LOOP-030`에서 고정한 preview/audit contract를 실제 runtime helper와 append-only sink interface에 연결한다.

## Decision

- `preview_contract`는 그대로 유지한다.
- 실제 runtime은 `preview_seed`를 추가로 만들어 `PREVIEW_REQUIRED` 응답과 execution trace contract seed에 함께 남긴다.
- persisted audit record는 raw trace가 아니라 `build_persisted_audit_record()` 결과만 sink에 append할 수 있다.
- 기본 sink는 no-op 성격의 `null_append_only`로 두고, 실제 저장소 backend는 다음 loop 밖으로 남긴다.

## Preview Seed

schema:

```json
{
  "schema_version": "v1.5.mutation_preview_seed.v1",
  "contract_schema_version": "v1.5.mutation_preview_contract.v1",
  "request_id": "req-123",
  "actor_category": "maintenance_mutation",
  "audit_scope": "maintenance",
  "tool": {
    "name": "reindex",
    "side_effect": "write"
  },
  "target": {
    "collection_key": "all",
    "reset": true,
    "include_compatibility_bundle": false,
    "impact_scope": "core_all_only"
  },
  "preview_fields": [
    "collection_key",
    "reset",
    "include_compatibility_bundle",
    "impact_summary"
  ],
  "preview": {
    "collection_key": "all",
    "reset": true,
    "include_compatibility_bundle": false,
    "impact_summary": "Reset and reindex all collection contents."
  },
  "expected_side_effect": "Reindex all collection contents.",
  "resolution": {
    "status": "resolved"
  },
  "redaction": {
    "audiences": ["internal", "public", "persisted"],
    "raw_content_allowed": false,
    "admin_code_allowed": false,
    "document_body_allowed": false
  }
}
```

tool별 helper 규칙:

- `reindex`
  - target seed에서 `collection_key`, `reset`, `include_compatibility_bundle`, `impact_scope`를 읽는다.
  - preview는 `impact_summary`를 포함한 안전한 운영 요약만 반환한다.
- `approve_upload_request`, `reject_upload_request`
  - `upload_service.get_upload_request_view()`로 현재 요청 상태를 읽는다.
  - preview는 `request_id`, `status`, `request_type`, `doc_key`, `expected_side_effect`만 반환한다.
  - `content_preview`, raw reason, admin code는 제외한다.

## Append-only Audit Sink

interface:

```python
class AppendOnlyAuditSink(Protocol):
    sink_type: str
    def append(self, record: dict[str, object]) -> dict[str, object]: ...
```

기본 구현:

- `NullAppendOnlyAuditSink`
  - 저장소 write 없이 `accepted=true` receipt만 반환
- `InMemoryAppendOnlyAuditSink`
  - 테스트용 append-only 메모리 sink

receipt 예시:

```json
{
  "accepted": true,
  "sink_type": "null_append_only",
  "record_schema_version": "v1.5.mutation_audit_record.v1",
  "sequence_id": null
}
```

검증 규칙:

- schema version이 `v1.5.mutation_audit_record.v1`이어야 한다.
- top-level `actor`, `raw_payload`가 있으면 거부한다.
- event에 `actor`, `admin_code`가 있으면 거부한다.
- outcome error에 raw `message`가 있으면 거부한다.

## Runtime Integration

- `services/tool_middleware_service.py`
  - `PREVIEW_REQUIRED` 응답에 `preview_contract`, `preview_seed`를 함께 포함한다.
  - execution trace/middleware metadata `contracts`에 `preview`, `preview_seed`, `persisted_audit`, `audit_sink`를 함께 남긴다.
- `services/tool_preview_service.py`
  - upload review/reindex preview seed helper를 담당한다.
- `services/tool_audit_sink_service.py`
  - append-only sink protocol, null/memory sink, persisted record validation을 담당한다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_tool_trace_service.py tests/test_tool_preview_service.py tests/test_tool_audit_sink_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

2026-04-12 후속 구현으로 `LOOP-032 V1.5 preview-confirmed mutation apply draft`, `LOOP-033 V1.5 mutation apply guard skeleton`까지 반영됐다. 다음 loop는 `LOOP-034 V1.5 mutation execution go/no-go review`다. 이 단계에서는 실제 write apply를 열기 전 필요한 사용자 결정 경계와 backend 조건을 고정한다.
