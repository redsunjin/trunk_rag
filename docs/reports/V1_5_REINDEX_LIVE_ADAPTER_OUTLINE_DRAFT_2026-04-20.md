# V1.5 Reindex Live Adapter Outline Draft - 2026-04-20

## Scope

- 대상 루프: `LOOP-044 V1.5 reindex live adapter outline draft`
- 기준 상태: `LOOP-043` operator runbook draft 반영 이후
- 목적: 실제 live execution은 계속 닫아 둔 채, future `reindex` live adapter가 current noop fallback/candidate stub contract 위에서 어떤 책임을 져야 하는지 outline 수준으로 고정한다.

## Decision

- `reindex`는 계속 `candidate_stub`까지만 선택한다.
- actual live adapter는 새 executor 이름(`reindex_mutation_adapter_live`)과 별도 contract outline으로만 정의한다.
- current executor contract의 `boundary.live_adapter_outline`은 future implementation을 여는 토글이 아니라, 다음 단계 test plan이 기대할 입력/출력/rollback awareness shape를 고정하는 문서화 seam이다.
- upload review와 public `/agent/*` surface는 이 outline에도 포함하지 않는다.

## Outline Contract

`services/mutation_executor_service.py`의 `boundary.live_adapter_outline`는 아래 의미를 가진다.

- `status=outline_only_deferred`
  - actual live implementation이 아직 없고, enablement verdict도 계속 `No-Go`라는 뜻이다.
- `target_executor_name=reindex_mutation_adapter_live`
  - future live path가 별도 executor identity를 갖도록 미리 고정한다.
- `current_executor_name=reindex_mutation_adapter_stub`
  - 현재는 candidate path가 stub까지만 존재한다는 연결점이다.
- `handoff_from_selection_state=candidate_stub`
  - live adapter는 noop fallback이 아니라 `candidate_stub` 다음 단계로만 붙는다.
- `execution_mode=off_by_default`
  - 문서/contract 추가만으로 execution이 열리지 않도록 다시 명시한다.

## Required Inputs

future live adapter가 받는 최소 입력은 아래로 고정한다.

1. `payload.collection`
2. `preview_seed.target.collection_key`
3. `apply_envelope.preview_ref`
4. `apply_envelope.intent.summary`
5. `persisted_audit_record.request_id`
6. `audit_sink_receipt.sequence_id`

의도:
- adapter는 raw 문서 본문이나 별도 public payload 없이도 current preview/apply/audit contract만으로 실행 대상을 식별해야 한다.
- audit linkage는 pre-existing append-only receipt 위에서 이어져야 한다.

## Expected Outputs

future live adapter는 최소한 아래 결과 shape를 남겨야 한다.

1. `result.reindex_summary`
2. `result.audit_receipt_ref`
3. `result.rollback_hint`

여기서 `rollback_hint`는 managed markdown 상태를 되돌리는 rollback plan이 아니라, local operator가 source documents 기준 재실행/복구 방향을 이해할 수 있게 하는 restore hint를 뜻한다.

## Rollback Awareness

- `reindex`는 `managed_state_write`가 아니므로 upload review와 같은 rollback plan을 요구하지 않는다.
- 대신 runtime derived state를 다시 만들 수 있어야 하므로 `rebuild_from_source_documents` 관점의 rollback awareness를 가진다.
- 따라서 outline contract는 `managed_state_rollback_required=false`, `operator_restore_hint_required=true`를 함께 고정한다.

이 구분으로 upload review boundary와 `reindex` live scope가 섞이지 않게 유지한다.

## Test Seams

`boundary.live_adapter_outline.test_seams`는 다음 세 가지를 다음 단계 검증 축으로 고정한다.

1. `noop_fallback_contract`
2. `candidate_stub_contract`
3. `future_live_adapter_opt_in_smoke`

의도:
- 기존 blocked path와 candidate stub path를 깨지 않고 유지한다.
- live adapter success path는 future opt-in smoke로만 추가한다.
- default smoke는 계속 `MUTATION_APPLY_NOT_ENABLED`를 기대해야 한다.

## Non-goals

- actual `reindex` live adapter 구현
- actual live execution enablement
- upload review execution
- public `/agent/*` endpoint

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

## Next Step

다음 loop는 `LOOP-045 V1.5 reindex live adapter test plan draft`다. 이 단계에서는 이번 outline contract를 기준으로 noop fallback/candidate stub/future live adapter smoke 범위를 테스트 계획으로 정리한다.
