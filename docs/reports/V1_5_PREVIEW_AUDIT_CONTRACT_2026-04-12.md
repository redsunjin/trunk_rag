# V1.5 Preview And Audit Contract - 2026-04-12

## Scope

- 대상 루프: `LOOP-030 V1.5 dry-run preview + audit persistence contract`
- 기준 커밋: `52e5830 feat(agent): add admin auth mutation gate`
- 목적: 실제 write apply 전에 필요한 preview payload 계약과 persisted audit record 계약을 코드/테스트/문서 기준으로 고정한다.

## Decision

- 실제 preview 생성과 저장소 sink 구현은 아직 하지 않는다.
- 대신 내부 runtime이 참조할 수 있는 `preview_contract`와 `persisted_audit_record` shape를 순수 함수로 고정한다.
- `PREVIEW_REQUIRED` 응답은 후속 loop가 채울 preview 결과의 최소 계약을 함께 반환한다.
- persisted audit record는 `persisted` audience redaction 결과만을 바탕으로 만들어 raw payload, admin code, document body를 포함하지 않는다.

## Preview Contract

schema:

```json
{
  "schema_version": "v1.5.mutation_preview_contract.v1",
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
  "expected_side_effect": "Reindex all collection contents.",
  "redaction": {
    "audiences": ["internal", "public", "persisted"],
    "raw_content_allowed": false,
    "admin_code_allowed": false,
    "document_body_allowed": false
  }
}
```

tool별 최소 target/preview field 규칙:

| tool | target seed | preview_fields |
| --- | --- | --- |
| `reindex` | `collection_key`, `reset`, `include_compatibility_bundle`, `impact_scope` | `collection_key`, `reset`, `include_compatibility_bundle`, `impact_summary` |
| `approve_upload_request` | `request_id`, `decision=approve`, optional `collection_override` | `request_id`, `status`, `request_type`, `doc_key`, `expected_side_effect` |
| `reject_upload_request` | `request_id`, `decision=reject`, `reason_code`, `reason_present`, `decision_note_present` | `request_id`, `status`, `request_type`, `doc_key`, `expected_side_effect` |

주의:

- `preview_contract`는 "실제 preview 결과"가 아니라 이후 preview seed builder가 채워야 할 최소 응답 shape다.
- `code`, `admin_code`, raw `reason`, raw document content는 contract target에 포함하지 않는다.

## Persisted Audit Record

schema:

```json
{
  "schema_version": "v1.5.mutation_audit_record.v1",
  "source_schema_version": "v1.5.tool_execution_trace.v1",
  "request_id": "req-123",
  "actor_category": "maintenance_mutation",
  "audit_scope": "maintenance",
  "tool": {
    "name": "reindex",
    "side_effect": "write"
  },
  "blocked_by": "mutation_policy_guard",
  "runtime": {
    "elapsed_ms": 5
  },
  "outcome": {
    "ok": false,
    "error": {
      "code": "PREVIEW_REQUIRED"
    }
  },
  "audit": {
    "events": [
      {
        "event": "tool.invoke.blocked",
        "elapsed_ms": 5,
        "code": "PREVIEW_REQUIRED",
        "tool": "reindex"
      }
    ]
  }
}
```

고정 규칙:

- source는 항상 `redact_execution_trace(..., audience="persisted")` 결과다.
- persisted audit record에는 raw actor string 대신 `actor_category`만 남긴다.
- `outcome.error`는 code/status 수준만 남기고 message는 저장하지 않는다.
- audit event는 `event`, `elapsed_ms`, `code`, `tool`만 남긴다.

## Implementation Note

- `services/tool_trace_service.py`
  - `build_preview_contract()`
  - `build_persisted_audit_record()`
  - `PREVIEW_CONTRACT_SCHEMA_VERSION`
  - `PERSISTED_AUDIT_RECORD_SCHEMA_VERSION`
- `services/tool_middleware_service.py`
  - `PREVIEW_REQUIRED` 응답에 `preview_contract`를 포함한다.
  - `execution_trace["contracts"]`와 middleware metadata에 `preview`, `persisted_audit` contract를 함께 남긴다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_tool_trace_service.py`
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

2026-04-12 후속 구현으로 `LOOP-031 V1.5 preview seed + audit sink skeleton`까지 반영됐다. 다음 loop는 `LOOP-032 V1.5 preview-confirmed mutation apply draft`이며, 이 단계에서는 `preview_seed`와 `audit_sink` receipt를 참조하는 apply envelope/error taxonomy를 고정한다.
