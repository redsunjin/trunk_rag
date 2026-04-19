# V1.5 Reindex Live Readiness Checklist Draft - 2026-04-19

## Scope

- 대상 루프: `LOOP-040 V1.5 reindex live readiness checklist draft`
- 기준 상태: `LOOP-039` mutation audit retention ops draft 반영 이후
- 목적: `reindex` live enablement 판단에 필요한 activation seam, upload review boundary, retention ops, smoke/runbook evidence 항목을 한 체크리스트로 고정한다.

## Checklist

| item | status | rationale | evidence |
| --- | --- | --- | --- |
| internal service only surface 유지 | ready | public `/agent/*` 없이 internal runtime 경계에서만 staged activation을 검토해야 한다. | `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md` |
| operator explicit activation 기본값 `off` | ready | 코드 merge만으로 write capability가 열리면 안 된다. | `services/mutation_executor_service.py`, `docs/reports/V1_5_REINDEX_EXECUTOR_ACTIVATION_SEAM_DRAFT_2026-04-18.md` |
| durable local audit receipt (`local_file_append_only`, `sequence_id`, `storage_path`) | ready | `reindex` candidate stub는 durable receipt가 있을 때만 판단 가능하다. | `services/tool_audit_sink_service.py`, `tests/test_tool_audit_sink_service.py` |
| retention/prune operator ownership 문서화 | ready | `90일 rolling_window`와 explicit local-operator prune가 staged activation과 충돌하면 안 된다. | `docs/reports/V1_5_MUTATION_AUDIT_RETENTION_OPS_DRAFT_2026-04-18.md` |
| upload review 별도 boundary 유지 | ready | upload review는 managed markdown/approval state write라 `reindex`와 같은 live scope로 볼 수 없다. | `docs/reports/V1_5_UPLOAD_REVIEW_EXECUTOR_BOUNDARY_REVIEW_2026-04-18.md` |
| preview-confirmed apply가 여전히 `MUTATION_APPLY_NOT_ENABLED`로 차단됨 | ready | readiness checklist 단계에서도 기본 정책은 off-by-default여야 한다. | `services/tool_middleware_service.py`, `services/tool_apply_service.py`, `tests/test_agent_runtime_service.py` |
| smoke evidence 항목 정의 | ready | blocked flow가 실제로 관찰 가능한지 체크해야 live enablement 논의가 가능하다. | `scripts/smoke_agent_runtime.py`, `tests/test_smoke_agent_runtime.py` |
| smoke evidence 패키징/리포트 | pending | existing smoke는 있지만 readiness evidence 형태로 묶어 둔 문서는 아직 없다. | 다음 loop `LOOP-041` |

## Required Evidence

`reindex` live enablement 전 확인해야 하는 최소 증빙은 아래와 같다.

1. `read_only_health_check`
   - internal runtime read path가 기본적으로 정상 동작하는지
2. `write_tool_blocked_read_only`
   - mutation permission이 없을 때 write tool이 allowlist 단계에서 막히는지
3. `write_tool_requires_admin_auth`
   - operator explicit activation 이전에 admin auth가 먼저 요구되는지
4. `write_tool_requires_mutation_intent`
   - auth만으로 충분하지 않고 explicit mutation intent가 필요한지
5. `write_tool_requires_preview`
   - apply 이전 preview contract/seed 생성이 강제되는지
6. `write_tool_apply_not_enabled`
   - valid apply envelope 뒤에도 기본값은 여전히 `MUTATION_APPLY_NOT_ENABLED`인지

이 증빙 자체를 문서와 실행 결과로 묶는 단계는 다음 loop(`LOOP-041`)에서 처리한다.

## Staged Activation Rule

- 현재 단계의 readiness checklist는 "enable now"를 의미하지 않는다.
- `reindex`는 candidate live scope이지만, checklist/evidence가 모두 갖춰져도 별도 go/no-go 판단 전까지는 off 상태를 유지한다.
- upload review는 checklist에 포함되더라도 `boundary_noop` 상태를 유지하며 같은 enablement 경로에 올리지 않는다.

## Non-goals

- 실제 `reindex` live execution 개방
- upload review live executor
- public `/agent/*` endpoint
- prune 자동화 구현

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-041 V1.5 mutation activation smoke evidence draft`다. 이 단계에서는 existing blocked flow smoke 결과를 readiness evidence 형태의 문서와 실행 출력으로 묶는다.
