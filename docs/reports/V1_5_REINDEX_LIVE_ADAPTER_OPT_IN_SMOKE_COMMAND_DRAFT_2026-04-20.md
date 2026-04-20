# V1.5 Reindex Live Adapter Opt-In Smoke Command Draft (2026-04-20)

## 목적
- default blocked smoke와 분리된 opt-in live binding smoke command를 concrete script surface로 고정한다.

## Command Surface
- CLI flag
  - `./.venv/bin/python scripts/smoke_agent_runtime.py --opt-in-live-binding`
- env toggle
  - `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING=1`

## Script Behavior
- default mode
  - `requested_live_binding=false`
  - apply request에 `executor_binding`을 넣지 않는다.
- opt-in mode
  - `requested_live_binding=true`
  - apply request에 아래 binding을 주입한다.
    - `binding_kind=explicit_live_adapter`
    - `binding_source=smoke_harness`
    - `executor_name=reindex_mutation_adapter_live`

## Guardrails
- script가 activation/audit backend를 자체로 강제하지 않는다.
- operator 또는 test harness가 기존 local-only activation 조건을 같이 맞춰야 한다.
- default smoke semantics는 그대로 유지된다.

## 코드 반영
- `scripts/smoke_agent_runtime.py`
  - `MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_ENV_KEY`
  - `MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE`
  - `run_smoke(opt_in_live_binding=...)`

## 검증
- `tests/test_smoke_agent_runtime.py`
  - default path는 `requested_live_binding=false`
  - opt-in path는 apply request에 expected binding을 주입한다
