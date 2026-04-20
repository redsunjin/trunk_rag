# V1.5 Reindex Live Adapter Opt-In Smoke Harness Draft - 2026-04-20

## Scope

- 대상 루프: `LOOP-048 V1.5 reindex live adapter opt-in smoke harness draft`
- 기준 상태: `LOOP-047` opt-in binding seam draft 반영 이후
- 목적: future `reindex` live adapter opt-in smoke를 default smoke와 분리된 별도 harness/command 관점으로 고정한다.

## Decision

- default smoke command는 계속 `./.venv/bin/python scripts/smoke_agent_runtime.py`다.
- future opt-in smoke는 default smoke 세트에 합치지 않는다.
- opt-in smoke는 explicit local-only binding이 있을 때만 의미가 있다.
- upload review는 opt-in smoke 범위에 넣지 않는다.

## Harness Contract

schema:
- `v1.5.reindex_live_adapter_smoke_harness.v1`

fields:
- `mode=separate_from_default_smoke`
- `default_command=./.venv/bin/python scripts/smoke_agent_runtime.py`
- `future_command_kind=explicit_live_adapter_binding_required`

## Prerequisites

future opt-in smoke 실행 전 아래 조건이 모두 필요하다.

1. `activation_requested`
2. `durable_audit_ready`
3. `explicit_live_adapter_binding`
4. `local_only_runtime_context`

의도:
- 환경 변수만 켜는 것으로는 충분하지 않다.
- explicit binding이 없는 상태에서는 opt-in smoke를 실행하지 않는다.
- local operator 또는 test harness가 binding을 주입하는 경로만 허용한다.

## Expected Evidence

future opt-in smoke가 남겨야 할 최소 evidence는 아래다.

1. `result.ok=true`
2. `result.mutation_executor.executor_name=reindex_mutation_adapter_live`
3. `result.result.reindex_summary`
4. `result.result.audit_receipt_ref`
5. `result.result.rollback_hint`

이 evidence는 success contract draft와 직접 연결된다.

## Isolation Rules

- `shares_default_smoke_suite=false`
- `upload_review_included=false`
- `public_surface_allowed=false`

즉, opt-in smoke는 아래와 분리된다.

- default blocked-flow smoke
- activation-on local-file candidate stub smoke
- upload review boundary smoke
- public `/agent/*` surface test

## Command Sketch

이번 단계에서는 actual command를 구현하지 않고, command 성격만 고정한다.

- default smoke:
  - `./.venv/bin/python scripts/smoke_agent_runtime.py`
- future opt-in smoke:
  - explicit live adapter binding을 주입한 별도 local-only harness/command

이 draft는 “무슨 커맨드를 써야 하는가”보다 “default smoke와 분리돼야 한다”는 경계를 먼저 고정한다.

## Non-goals

- actual live adapter implementation
- actual live execution enablement
- upload review smoke
- public `/agent/*` endpoint

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

## Next Step

다음 loop는 `LOOP-049 V1.5 reindex live adapter executor injection protocol draft`다. 이 단계에서는 explicit local-only binding이 runtime/test harness에 어떻게 주입되는지 protocol 수준으로 정리한다.
