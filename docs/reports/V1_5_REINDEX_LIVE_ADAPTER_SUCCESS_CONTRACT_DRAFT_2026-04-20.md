# V1.5 Reindex Live Adapter Success Contract Draft - 2026-04-20

## Scope

- 대상 루프: `LOOP-046 V1.5 reindex live adapter success contract draft`
- 기준 상태: `LOOP-045` live adapter test plan draft 반영 이후
- 목적: actual live execution을 열지 않은 상태에서, future `reindex` live adapter가 반환해야 할 success/failure result shape와 error taxonomy를 contract draft 수준으로 고정한다.

## Decision

- success/failure contract는 `boundary.live_adapter_outline` 아래의 metadata로만 추가한다.
- current runtime path는 여전히 `noop_fallback` 또는 `candidate_stub`까지만 노출한다.
- success contract는 future opt-in live adapter smoke가 기대할 최소 결과 shape를 고정하는 용도다.
- failure taxonomy는 default blocked path 에러와 별개이며, actual live adapter가 생긴 뒤 executor 내부 failure만 표현한다.

## Success Contract

schema:
- `v1.5.reindex_live_adapter_result.v1`

required fields:
1. `result.reindex_summary.collection_key`
2. `result.reindex_summary.operation`
3. `result.reindex_summary.source_basis`
4. `result.audit_receipt_ref.sequence_id`
5. `result.rollback_hint.mode`

shape notes:
- `reindex_summary.operation=rebuild_vector_index`
- `reindex_summary.source_basis=source_documents_snapshot`
- `audit_receipt_ref`는 pre-existing append-only receipt와 연결 가능한 reference여야 한다.
- `rollback_hint.mode=rebuild_from_source_documents`

핵심 의도:
- success path는 managed markdown rollback이 아니라 source documents 기준 rebuild/restore hint를 남겨야 한다.
- live adapter가 생겨도 upload review와 같은 approval-state write contract로 확장하지 않는다.

## Failure Taxonomy

schema:
- `v1.5.reindex_live_adapter_error.v1`

codes:
1. `REINDEX_TARGET_MISMATCH`
   - stage: `contract_validation`
   - retryable: `false`
   - 의미: payload/apply/preview target이 서로 맞지 않는다.
2. `REINDEX_AUDIT_LINKAGE_INVALID`
   - stage: `audit_linkage`
   - retryable: `false`
   - 의미: append-only receipt reference가 success result와 안전하게 연결되지 않는다.
3. `REINDEX_RUNTIME_EXECUTION_FAILED`
   - stage: `executor_runtime`
   - retryable: `true`
   - 의미: reindex runtime 수행 자체가 실패했다.
4. `REINDEX_ROLLBACK_HINT_UNAVAILABLE`
   - stage: `post_execution`
   - retryable: `true`
   - 의미: reindex는 끝났지만 operator restore hint를 만들지 못했다.

## Boundary Invariants

success/failure contract가 추가돼도 아래는 그대로 유지한다.

- `family=reindex`
- `classification=derivative_runtime_state`
- `managed_state_write=false`
- `requires_rollback_plan=false`
- `rollback_awareness.mode=rebuild_from_source_documents`
- default path remains `MUTATION_APPLY_NOT_ENABLED`

## Test Implication

이번 단계에서 테스트가 기대해야 하는 것은 실제 success path가 아니라, contract seed가 boundary metadata에 안정적으로 존재한다는 점이다.

- executor unit: success/failure contract seed 노출 확인
- middleware integration: blocked/candidate path가 이 metadata 추가로 깨지지 않는지 확인
- agent runtime: execution trace/error contract에 같은 boundary shape가 유지되는지 확인

future actual success-path 검증은 `future_live_adapter_opt_in_smoke` 또는 adapter-specific test에서만 다룬다.

## Non-goals

- actual live adapter implementation
- actual live execution enablement
- upload review success path
- public `/agent/*` endpoint

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

## Next Step

다음 loop는 `LOOP-047 V1.5 reindex live adapter opt-in binding seam draft`다. 이 단계에서는 default path를 바꾸지 않고 future live adapter를 explicit local-only binding으로만 주입하는 selection seam을 정리한다.
