# V1.5 Reindex Live Adapter Opt-In Binding Seam Draft - 2026-04-20

## Scope

- 대상 루프: `LOOP-047 V1.5 reindex live adapter opt-in binding seam draft`
- 기준 상태: `LOOP-046` live adapter success contract draft 반영 이후
- 목적: future `reindex` live adapter가 default path를 바꾸지 않고, explicit local-only binding으로만 주입되도록 selection seam을 고정한다.

## Decision

- default selection은 계속 `reindex_mutation_adapter_stub`다.
- future live adapter는 registered default binding이 아니라 `runtime_injected_executor_binding` 성격의 explicit override로만 붙는다.
- opt-in binding owner는 `local_operator_or_test_harness`로 제한한다.
- upload review는 이 binding seam을 공유하지 않는다.

## Binding Contract

schema:
- `v1.5.reindex_live_adapter_binding.v1`

fields:
- `mode=explicit_local_only`
- `binding_source=runtime_injected_executor_binding`
- `binding_owner=local_operator_or_test_harness`
- `default_executor_name=reindex_mutation_adapter_stub`
- `opt_in_executor_name=reindex_mutation_adapter_live`

## Selection Precedence

future opt-in binding이 생겨도 selection precedence는 아래 순서를 따른다.

1. `tool_registration_boundary`
2. `activation_guard`
3. `candidate_stub_default`
4. `explicit_live_binding_override`

의도:
- tool registration과 upload review boundary가 먼저 판정된다.
- activation guard가 충족되지 않으면 opt-in binding도 고려하지 않는다.
- activation guard가 충족돼도 default는 여전히 `candidate_stub`다.
- explicit binding이 있을 때만 future live adapter override가 가능하다.

## Required Signals

future live adapter override가 고려되려면 최소한 아래 신호가 동시에 있어야 한다.

1. `activation_requested`
2. `durable_audit_ready`
3. `explicit_live_adapter_binding`

즉, 환경 변수만으로는 live adapter가 열리지 않는다. explicit binding seam이 별도로 있어야 한다.

## Guardrails

- `public_surface_allowed=false`
- `shared_with_upload_review=false`

이 guardrail로 다음 원칙을 유지한다.

- public `/agent/*` surface에서는 이 seam을 다루지 않는다.
- upload review success path와 같은 binding 메커니즘으로 합치지 않는다.
- default blocked/candidate smoke는 계속 기존 의미를 유지한다.

## Test Implication

이번 단계에서 고정된 검증 포인트:

- executor boundary metadata에 opt-in binding seam이 존재한다.
- current blocked path와 candidate stub path는 그대로 유지된다.
- future opt-in smoke는 explicit binding injection이 없으면 실행 대상이 아니다.

## Non-goals

- actual live adapter implementation
- actual live execution enablement
- upload review binding
- public `/agent/*` endpoint

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

## Next Step

다음 loop는 `LOOP-048 V1.5 reindex live adapter opt-in smoke harness draft`다. 이 단계에서는 explicit local-only binding seam을 실제 default smoke와 분리된 별도 harness/command 관점으로 정리한다.
