# V1.5 Mutation Activation Smoke Evidence - 2026-04-19

## Scope

- 대상 루프: `LOOP-041 V1.5 mutation activation smoke evidence draft`
- 기준 상태: `LOOP-040` reindex live readiness checklist draft 반영 이후
- 목적: existing blocked-flow smoke 결과를 readiness evidence로 고정하고, `reindex` live readiness checklist와 실제 실행 증빙의 연결을 문서화한다.

## Commands

- `./.venv/bin/python -m pytest -q tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`

## Observed Result

- smoke schema: `v1.5.mutation_activation_smoke.v1`
- overall result: `ok=true`
- default runtime path는 read-only health check를 통과했다.
- mutation candidate write path는 allowlist, admin auth, mutation intent, preview, apply 단계별로 순차 차단됐다.
- preview-confirmed apply path는 여전히 `MUTATION_APPLY_NOT_ENABLED`로 막혔고, `mutation_executor` evidence는 `noop_fallback` + `activation_guard_blocked`를 유지했다.

## Evidence Mapping

| smoke check | observed evidence | readiness linkage |
| --- | --- | --- |
| `read_only_health_check` | `ok=true`, `selected_tool=health_check` | internal runtime read path가 기본적으로 살아 있는지 확인 |
| `write_tool_blocked_read_only` | `error_code=TOOL_NOT_ALLOWED`, `blocked_by=tool_allowlist` | mutation permission 없는 기본 경로에서 write tool이 바로 열리지 않는지 확인 |
| `write_tool_requires_admin_auth` | `error_code=ADMIN_AUTH_REQUIRED`, `blocked_by=mutation_policy_guard` | operator explicit activation 논의 이전에 admin auth gate가 선행되는지 확인 |
| `write_tool_requires_mutation_intent` | `error_code=MUTATION_INTENT_REQUIRED`, `blocked_by=mutation_policy_guard` | auth만으로 충분하지 않고 explicit mutation intent가 요구되는지 확인 |
| `write_tool_requires_preview` | `error_code=PREVIEW_REQUIRED`, `blocked_by=mutation_policy_guard`, `apply_envelope.schema_version=v1.5.mutation_apply_envelope.v1` | preview-confirmed apply handshake seed가 생성되는지 확인 |
| `write_tool_apply_not_enabled` | `error_code=MUTATION_APPLY_NOT_ENABLED`, `blocked_by=mutation_apply_guard`, `mutation_executor.selection_state=noop_fallback`, `mutation_executor.activation_blocked_by=[activation_not_requested,durable_audit_not_ready]` | live execution이 아직 off-by-default이며, activation request + durable audit receipt 없이는 `reindex`도 noop fallback에 머무는지 확인 |

## Key Findings

1. `scripts/smoke_agent_runtime.py`는 이제 `schema_version`, `apply_envelope`, `audit_sink`, `mutation_executor` 요약을 함께 남겨 readiness evidence 용도로 직접 재사용할 수 있다.
2. default smoke 환경에서는 `audit_sink.sink_type=null_append_only`, `mutation_executor.audit_sink_type=null_append_only`가 관찰돼 durable local audit backend가 아직 activation precondition으로 남아 있음을 보여 준다.
3. apply 단계에서도 `mutation_executor.executor_name=noop_mutation_executor`, `selection_reason=activation_guard_blocked`가 유지돼, current default가 "preview 가능, apply 불가" 상태임이 명확하다.
4. upload review live executor는 이번 smoke 범위에 포함하지 않았고, `LOOP-038`에서 고정한 `boundary_noop` 분리는 그대로 유지된다.

## Notes

- 실행 중 `urllib3` LibreSSL warning과 telemetry capture warning이 출력됐지만 smoke result 자체는 `ok=true`로 종료됐다.
- 이번 evidence는 staged activation readiness를 위한 관측 자료이며, 실제 live execution enablement를 의미하지 않는다.

## Next Step

다음 loop는 `LOOP-042 V1.5 reindex activation checkpoint review`다. 이 단계에서는 checklist와 smoke evidence를 바탕으로 `reindex` staged activation에 남은 blocker와 checkpoint 질문만 고정한다.
