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
8. concrete executor skeleton
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_CONCRETE_EXECUTOR_SKELETON_DRAFT_2026-04-21.md`
9. concrete smoke evidence
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_CONCRETE_SMOKE_EVIDENCE_DRAFT_2026-04-21.md`
10. top-level success promotion rule
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_DRAFT_2026-04-21.md`
11. adapter-specific failure taxonomy seam
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_FAILURE_TAXONOMY_DRAFT_2026-04-21.md`

### Verified Repeatedly

반복적으로 유지 중인 공통 검증:

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

최근 루프들(`LOOP-045` ~ `LOOP-054`)은 같은 타깃 pytest 스택을 유지한 채 단계적으로 확장됐고, 최신 closeout 기준 `49 passed`다.

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
4. explicit live binding concrete skeleton path
   - 기대: `live_result_skeleton`
   - 기대 에러: `MUTATION_APPLY_NOT_ENABLED`
   - 기대 sidecar: `mutation_executor_result`

### Future Paths

1. actual execution enablement go/no-go review
   - 기대: `mutation_apply_guard_execution_enabled` 전환 가능 조건과 blocker 판정
   - 상태: next draft

## Recommended Testing Order

다음 검증 순서는 아래로 고정한다.

1. default blocked-flow smoke 유지 확인
2. activation-on local-file candidate stub 유지 확인
3. explicit local-only opt-in smoke harness 정의
4. concrete executor skeleton smoke evidence 검증
5. top-level success promotion 규칙 정리
6. adapter-specific runtime failure taxonomy 검증

## Open Testing Gaps

아직 남아 있는 테스트 갭:

1. actual execution enablement 이후 smoke 업데이트 기준
2. real side-effect rollback drill 여부

## Notes

- 현재는 설계/contract 단계라서 전체 pytest나 live gate보다 타깃 mutation/runtime/smoke suite가 우선이다.
- 실제 execution을 열기 전까지는 default smoke가 계속 실패 아닌 “blocked success” 성격으로 유지되는 것이 맞다.

## Next Step

다음 구현은 `LOOP-057 V1.5 reindex live adapter execution enablement go/no-go review`다. 이 문서는 이후 loop들의 테스트 상태/로드맵 기준 요약본으로 재사용한다.
