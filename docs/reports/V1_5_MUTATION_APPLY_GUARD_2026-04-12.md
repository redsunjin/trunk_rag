# V1.5 Mutation Apply Guard Skeleton - 2026-04-12

## Scope

- 대상 루프: `LOOP-033 V1.5 mutation apply guard skeleton`
- 기준 상태: `LOOP-032` apply envelope draft 반영 이후
- 목적: preview-confirmed apply envelope를 실제 middleware guard helper에 연결하되, 아직 write execution은 열지 않는다.

## Decision

- `mutation_policy_guard`는 admin auth, mutation intent, preview seed까지 확인하고 preview 단계 draft를 노출한다.
- `mutation_apply_guard`는 제출된 `apply_envelope`가 있을 때만 preview seed와 대조해 apply handshake를 검증한다.
- validation이 통과해도 실제 adapter는 호출하지 않고 `MUTATION_APPLY_NOT_ENABLED`로 멈춘다.

## Guard Flow

1. `mutation_policy_guard`
   - write candidate에 대해 `ADMIN_AUTH_REQUIRED`
   - 이후 `MUTATION_INTENT_REQUIRED`
   - 이후 preview seed가 필요하면 `PREVIEW_REQUIRED`
   - 단, `apply_envelope`가 함께 들어오면 preview 단계는 통과시키고 다음 guard로 넘긴다.
2. `mutation_apply_guard`
   - `preview_ref` mismatch면 `PREVIEW_REFERENCE_MISMATCH`
   - `audit_ref` 누락이면 `AUDIT_SINK_RECEIPT_REQUIRED`
   - invalid receipt면 `AUDIT_SINK_RECEIPT_INVALID`
   - missing intent summary면 `MUTATION_INTENT_SUMMARY_REQUIRED`
   - 모두 통과해도 `MUTATION_APPLY_NOT_ENABLED`

## Trace And Error Contract

- middleware 순서는 `mutation_policy_guard -> mutation_apply_guard -> unsafe_action_guard`로 고정한다.
- execution trace detail에는 `apply_envelope_present`를 남긴다.
- blocked error에는 `submitted_apply_envelope`를 남기고, current preview 기반 `apply_envelope` draft도 함께 노출한다.
- persisted audit record와 sink receipt는 기존 preview/audit contract를 그대로 재사용한다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_tool_trace_service.py tests/test_tool_preview_service.py tests/test_tool_audit_sink_service.py tests/test_tool_apply_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-034 V1.5 mutation execution go/no-go review`다. 이 단계에서는 실제 write apply를 열기 전에 필요한 사용자 결정 경계, backend 선택, retention 범위를 문서로 고정한다.
