# V1.5 Mutation Apply Draft - 2026-04-12

## Scope

- 대상 루프: `LOOP-032 V1.5 preview-confirmed mutation apply draft`
- 기준 커밋: `5df8cd1 feat(agent): add preview seed and audit sink`
- 목적: `preview_seed`, append-only audit sink receipt, mutation intent summary를 하나의 apply handshake envelope로 고정한다.

## Decision

- 실제 write adapter 호출은 아직 열지 않는다.
- 대신 preview 단계가 반환하는 `apply_envelope` draft와 apply 단계가 제출해야 하는 최소 schema를 고정한다.
- error taxonomy는 preview reference 누락/불일치, audit receipt 누락/불량, mutation intent summary 누락을 서로 다른 code로 분리한다.

## Apply Envelope

schema:

```json
{
  "schema_version": "v1.5.mutation_apply_envelope.v1",
  "actor_category": "maintenance_mutation",
  "audit_scope": "maintenance",
  "tool": {
    "name": "reindex",
    "side_effect": "write"
  },
  "preview_ref": {
    "preview_schema_version": "v1.5.mutation_preview_seed.v1",
    "tool_name": "reindex",
    "target": {
      "collection_key": "all",
      "reset": true,
      "include_compatibility_bundle": false,
      "impact_scope": "core_all_only"
    }
  },
  "audit_ref": {
    "sink_type": "null_append_only",
    "record_schema_version": "v1.5.mutation_audit_record.v1",
    "accepted": true,
    "sequence_id": null
  },
  "intent": {
    "summary": "reindex all"
  },
  "apply_control": {
    "execution_enabled": false,
    "required_signals": ["preview_ref", "audit_ref", "intent.summary"]
  }
}
```

고정 규칙:

- `preview_ref`는 현재 `preview_seed`의 schema/tool/target과 정확히 일치해야 한다.
- `audit_ref`는 append-only sink receipt에서 `accepted=true`, `sink_type`, `record_schema_version`을 가져와야 한다.
- `intent.summary`는 preview 단계에서 입력한 mutation intent를 그대로 유지한다.
- `execution_enabled`는 아직 `false`로 고정한다.

## Error Taxonomy

- `PREVIEW_REFERENCE_REQUIRED`
- `PREVIEW_REFERENCE_MISMATCH`
- `AUDIT_SINK_RECEIPT_REQUIRED`
- `AUDIT_SINK_RECEIPT_INVALID`
- `MUTATION_INTENT_SUMMARY_REQUIRED`

## Runtime Integration

- `services/tool_apply_service.py`
  - `build_mutation_apply_envelope()`
  - `validate_mutation_apply_envelope()`
  - envelope schema version과 error code 상수
- `services/tool_middleware_service.py`
  - `PREVIEW_REQUIRED` 응답에 `apply_envelope` draft를 함께 포함한다.
  - execution trace/middleware metadata `contracts`에 `apply_envelope` draft를 함께 남긴다.
- `services/agent_runtime_service.py`
  - `AgentRuntimeRequest.apply_envelope`를 추가하고 entry metadata에 `apply_envelope_present`를 남긴다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_tool_trace_service.py tests/test_tool_preview_service.py tests/test_tool_audit_sink_service.py tests/test_tool_apply_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-033 V1.5 mutation apply guard skeleton`이다. 이 단계에서는 apply envelope를 실제 middleware guard에 연결하고, valid envelope도 실행 대신 `MUTATION_APPLY_NOT_ENABLED`로 차단한다.
