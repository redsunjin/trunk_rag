# V1.5 Reindex Live Adapter Test Plan Draft - 2026-04-20

## Scope

- 대상 루프: `LOOP-045 V1.5 reindex live adapter test plan draft`
- 기준 상태: `LOOP-044` live adapter outline contract 반영 이후
- 목적: `boundary.live_adapter_outline`가 고정한 입력/출력/rollback awareness를 기준으로, noop fallback/candidate stub/future live adapter smoke를 어떤 층위에서 검증할지 test plan으로 정리한다.

## Test Plan Principles

1. default path는 계속 `MUTATION_APPLY_NOT_ENABLED`여야 한다.
2. `reindex` future live adapter success path는 explicit opt-in seam에서만 검증한다.
3. upload review는 같은 test plan에 넣더라도 `boundary_noop` separate boundary로 유지한다.
4. public `/agent/*` surface는 test plan 대상이 아니다.

## Verification Layers

### 1. Executor Unit Layer

대상: `tests/test_mutation_executor_service.py`

유지할 케이스:
- `tool_not_registered` default noop
- `reindex` + activation off -> `noop_fallback`
- `reindex` + activation on + durable audit missing -> `noop_fallback`
- `reindex` + activation on + durable audit ready -> `candidate_stub`
- upload review tools -> `boundary_noop`

후속 추가 케이스:
- future live adapter가 실제로 생기면 `candidate_stub` 이후 success contract를 별도 explicit binding으로 검증한다.
- 그 success test는 default selection을 바꾸지 않고 fake/opt-in adapter seam으로만 추가한다.

## 2. Middleware Integration Layer

대상: `tests/test_tool_middleware_service.py`

유지할 케이스:
- `mutation_apply_guard`가 여전히 `MUTATION_APPLY_NOT_ENABLED`를 반환한다.
- blocked path/error path에 `mutation_executor` contract가 execution trace까지 그대로 전파된다.
- activation-on durable audit 경로에서도 `candidate_stub`까지 보이되 실제 apply는 성공하지 않는다.

후속 추가 케이스:
- future live adapter가 생기면 middleware는 success/failure result shape를 redaction-safe contract로 남기는지만 검증한다.
- adapter 내부 reindex 로직 자체는 middleware test가 아니라 adapter-focused unit/integration test에서 검증한다.

## 3. Agent Runtime Integration Layer

대상: `tests/test_agent_runtime_service.py`

유지할 케이스:
- actor policy, admin auth, mutation intent, preview, apply guard가 현재 순서대로 유지된다.
- activation-on durable audit 경로에서 `candidate_stub` contract가 agent entry error payload와 execution trace에 그대로 노출된다.

후속 추가 케이스:
- future live adapter success path는 agent runtime에서 “single tool apply result forwarding”만 본다.
- live adapter 내부 domain logic은 agent runtime layer에서 중복 검증하지 않는다.

## 4. Smoke Layer

대상:
- `tests/test_smoke_agent_runtime.py`
- `scripts/smoke_agent_runtime.py`

유지할 smoke:
1. baseline default smoke
   - `write_tool_apply_not_enabled`
   - `selection_state=noop_fallback`
2. activation-on local-file smoke
   - `selection_state=candidate_stub`
   - error는 여전히 `MUTATION_APPLY_NOT_ENABLED`

future opt-in smoke:
- 이름: `future_live_adapter_opt_in_smoke`
- 목적: explicit local-only seam에서 success path result shape를 점검
- guardrail:
  - default smoke 세트에 합치지 않는다.
  - operator activation + durable audit + explicit adapter binding이 모두 있을 때만 실행한다.
  - upload review는 포함하지 않는다.

## 5. Result Contract Checks

future live adapter가 추가되면 최소한 아래 shape를 검증 대상으로 둔다.

- `result.reindex_summary`
- `result.audit_receipt_ref`
- `result.rollback_hint`

동시에 아래 invariants를 유지해야 한다.

- `boundary.family=reindex`
- `boundary.classification=derivative_runtime_state`
- `managed_state_write=false`
- `requires_rollback_plan=false`
- `rollback_awareness.mode=rebuild_from_source_documents`

## Deferred Items

이번 test plan이 아직 다루지 않는 항목:

- actual live adapter implementation
- actual live execution enablement
- public `/agent/*` surface test
- upload review success-path test

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

## Next Step

다음 loop는 `LOOP-046 V1.5 reindex live adapter success contract draft`다. 이 단계에서는 actual live execution을 열지 않고, future live adapter success/failure result shape와 error taxonomy를 draft 수준으로 고정한다.
