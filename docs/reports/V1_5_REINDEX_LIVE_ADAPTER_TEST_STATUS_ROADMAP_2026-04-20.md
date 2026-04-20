# V1.5 Reindex Live Adapter Test Status Roadmap - 2026-04-20

## Current Status

현재 `reindex` live adapter 관련 테스트 상태는 아래와 같다.

### Completed

1. blocked-flow smoke evidence
   - 문서: `docs/reports/V1_5_MUTATION_ACTIVATION_SMOKE_EVIDENCE_2026-04-19.md`
   - 핵심: default path는 계속 `MUTATION_APPLY_NOT_ENABLED`
2. activation checkpoint / operator runbook
   - 문서: `docs/reports/V1_5_REINDEX_ACTIVATION_CHECKPOINT_REVIEW_2026-04-19.md`
   - 문서: `docs/reports/V1_5_REINDEX_ACTIVATION_OPERATOR_RUNBOOK_DRAFT_2026-04-19.md`
3. live adapter outline
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OUTLINE_DRAFT_2026-04-20.md`
4. live adapter test plan
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TEST_PLAN_DRAFT_2026-04-20.md`
5. live adapter success/failure contract
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_SUCCESS_CONTRACT_DRAFT_2026-04-20.md`
6. explicit local-only opt-in binding seam
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OPT_IN_BINDING_SEAM_DRAFT_2026-04-20.md`
7. opt-in smoke harness separation draft
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OPT_IN_SMOKE_HARNESS_DRAFT_2026-04-20.md`

### Verified Repeatedly

반복적으로 유지 중인 공통 검증:

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

최근 루프들(`LOOP-045` ~ `LOOP-048`)은 위 타깃 pytest에서 `38 passed` 기준으로 닫혔다.

## Test Matrix

### Current Guaranteed Paths

1. default blocked path
   - 기대: `noop_fallback`
   - 기대 에러: `MUTATION_APPLY_NOT_ENABLED`
2. activation-on + durable audit ready path
   - 기대: `candidate_stub`
   - 기대 에러: `MUTATION_APPLY_NOT_ENABLED`
3. upload review path
   - 기대: `boundary_noop`

### Future Paths

1. explicit local-only opt-in smoke
   - 기대: `reindex_mutation_adapter_live`
   - 상태: draft only
2. adapter-specific success/failure tests
   - 기대: `reindex_summary`, `audit_receipt_ref`, `rollback_hint`
   - 상태: draft only

## Recommended Testing Order

다음 검증 순서는 아래로 고정한다.

1. default blocked-flow smoke 유지 확인
2. activation-on local-file candidate stub 유지 확인
3. explicit local-only opt-in smoke harness 정의
4. live adapter success-path contract 검증
5. adapter-specific runtime failure taxonomy 검증

## Open Testing Gaps

아직 남아 있는 테스트 갭:

1. explicit live adapter binding이 실제로 주입되는 harness/command 정의
2. success-path result payload 검증
3. executor runtime failure 재현 케이스
4. rollback hint unavailable 경로 검증

## Notes

- 현재는 설계/contract 단계라서 전체 pytest나 live gate보다 타깃 mutation/runtime/smoke suite가 우선이다.
- 실제 execution을 열기 전까지는 default smoke가 계속 실패 아닌 “blocked success” 성격으로 유지되는 것이 맞다.

## Next Step

다음 구현은 `LOOP-049 V1.5 reindex live adapter executor injection protocol draft`다. 이 문서는 이후 loop들의 테스트 상태/로드맵 기준 요약본으로 재사용한다.
