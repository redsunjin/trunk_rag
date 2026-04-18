# V1.5 Upload Review Executor Boundary Review - 2026-04-18

## Scope

- 대상 루프: `LOOP-038 V1.5 upload review executor boundary review`
- 기준 상태: `LOOP-037` reindex executor activation seam 반영 이후
- 목적: upload review execution을 `reindex` activation seam과 섞지 않고, managed markdown/approval state 변경에 필요한 별도 rollback/audit precondition을 executor contract와 테스트 기준으로 고정한다.

## Decision

- `services/mutation_executor_service.py`는 upload review tool을 generic unregistered noop로 취급하지 않고, 별도 `boundary_noop` selection으로 분리한다.
- `approve_upload_request`, `reject_upload_request`는 둘 다 `live_candidate_allowed=false`로 고정한다.
- `approve_upload_request`는 managed markdown active 상태를 바꿀 수 있으므로 `reject_upload_request`보다 더 강한 rollback/document binding precondition을 요구한다.
- `reject_upload_request`는 indexed document content를 바꾸지 않더라도 approval state write이므로 decision audit contract review 없이 live candidate로 올리지 않는다.
- `DOC_RAG_AGENT_MUTATION_EXECUTION=1`과 durable local audit receipt가 준비돼 있어도 upload review는 candidate stub로 승격되지 않는다.

## Boundary Contract

executor contract의 nested `boundary`는 아래를 드러낸다.

- 공통 필드:
  - `family`
  - `classification`
  - `live_candidate_allowed`
  - `managed_state_write`
  - `approval_state_write`
  - `requires_durable_audit_receipt`
  - `requires_rollback_plan`
  - `requires_managed_state_snapshot`
  - `requires_document_version_binding`
  - `requires_decision_audit`
  - `required_preconditions`
  - `blocked_by`

### approve_upload_request

- `classification=managed_doc_activation`
- `managed_state_write=true`
- `approval_state_write=true`
- 추가 precondition:
  - `separate_upload_review_go_no_go`
  - `decision_audit_contract`
  - `managed_state_snapshot`
  - `document_version_binding`
  - `rollback_plan`
- blocked reason:
  - `upload_review_scope_deferred`
  - `managed_state_rollback_not_ready`
  - `document_version_binding_not_reviewed`

### reject_upload_request

- `classification=request_decision_only`
- `managed_state_write=false`
- `approval_state_write=true`
- 추가 precondition:
  - `separate_upload_review_go_no_go`
  - `decision_audit_contract`
- blocked reason:
  - `upload_review_scope_deferred`
  - `decision_audit_contract_not_reviewed`

## Selection Rules

1. `reindex`
   - 기존 `activation_guard_blocked` / `candidate_stub` 흐름 유지
2. `approve_upload_request`, `reject_upload_request`
   - `executor_name=noop_mutation_executor`
   - `selection_state=boundary_noop`
   - `selection_reason=upload_review_scope_deferred`
   - live candidate로 승격하지 않음
3. 그 외 미등록 mutation tool
   - 기존 `default_noop` 유지

## Runtime/Test Integration

- `tests/test_mutation_executor_service.py`
  - approve/reject upload review가 서로 다른 `boundary.classification`과 precondition을 남기는지 검증한다.
- `tests/test_tool_middleware_service.py`
  - activation on + durable local audit ready 조건에서도 approve upload review apply는 `boundary_noop`로 남는지 검증한다.
- `tests/test_agent_runtime_service.py`
  - agent entry도 같은 upload review boundary contract를 error/execution trace에 노출하는지 검증한다.

## Non-goals

- 실제 approve/reject live execution 개방
- upload review 전용 live adapter 추가
- public `/agent/*` endpoint
- rollback automation 또는 prune job 구현

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

결과:

- `38 passed`
- `[roadmap-harness] ready`
- formatting/whitespace issue 없음

## Next Step

다음 loop는 `LOOP-039 V1.5 mutation audit retention ops draft`다. 이 단계에서는 `90일 rolling_window`, explicit prune ownership, staged activation 문구를 operator-facing 기준으로 정리한다.
