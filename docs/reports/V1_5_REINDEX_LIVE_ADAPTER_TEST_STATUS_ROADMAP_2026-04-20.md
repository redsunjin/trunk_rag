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
12. execution enablement go/no-go review
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_GO_NO_GO_REVIEW_2026-04-21.md`
   - 핵심: actual execution `No-Go`, next planning `Go` for pre-execution handoff seam
13. pre-execution audit/executor handoff seam
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PRE_EXECUTION_HANDOFF_SEAM_DRAFT_2026-04-21.md`
   - 핵심: actual side effect 전 durable audit receipt, mutation executor router, explicit binding, success/failure promotion handoff 순서 고정
14. fake/sandboxed executor smoke seam
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_FAKE_EXECUTOR_SMOKE_SEAM_DRAFT_2026-04-21.md`
   - 핵심: actual index mutation 없이 success/failure promotion smoke evidence 고정
15. mutation apply executor router dry-run seam
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_MUTATION_APPLY_ROUTER_DRY_RUN_SEAM_DRAFT_2026-04-22.md`
   - 핵심: blocked apply path에서 direct `_tool_reindex`/`index_service.reindex` 호출 없이 mutation executor router dry-run evidence 고정
16. execution enablement checkpoint review
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`
   - 핵심: actual execution `No-Go`, next planning `Go` for pre-side-effect executor router implementation draft
17. pre-side-effect executor router implementation draft
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PRE_SIDE_EFFECT_EXECUTOR_ROUTER_IMPLEMENTATION_DRAFT_2026-04-22.md`
   - 핵심: valid apply 이후 direct tool handler 전에 durable audit receipt와 mutation executor router dry-run 실행
18. top-level promotion router implementation draft
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_ROUTER_IMPLEMENTATION_DRAFT_2026-04-22.md`
   - 핵심: executor success/failure sidecar를 future top-level apply `result`/`error` surface로 매핑하는 router evidence 고정
19. execution enablement final checkpoint review
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_FINAL_CHECKPOINT_REVIEW_2026-04-22.md`
   - 핵심: actual execution `No-Go`, guarded live executor implementation planning `Go`
20. guarded live executor implementation draft
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_IMPLEMENTATION_DRAFT_2026-04-22.md`
   - 핵심: explicit local-only `binding_stage=guarded_live_executor`에서만 `index_service.reindex()` 호출 seam 검증
21. guarded live executor smoke command draft
   - 문서: `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_SMOKE_COMMAND_DRAFT_2026-04-22.md`
   - 핵심: `--opt-in-live-binding-stage-guarded` command surface와 guarded runtime sidecar summary 고정

### Verified Repeatedly

반복적으로 유지 중인 공통 검증:

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

최근 루프들(`LOOP-045` ~ `LOOP-066`)은 타깃 pytest 스택을 유지한 채 단계적으로 확장됐고, 최신 `LOOP-066` closeout 기준 smoke/executor target은 `24 passed`다.

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
   - 기대 sidecar: `mutation_executor_result`, `mutation_success_promotion`, `mutation_top_level_promotion_router`
5. explicit guarded live executor path
   - 기대: `guarded_live_executor`
   - 기대: direct tool handler bypass, `index_service.reindex()` 호출 seam evidence
   - 기대 top-level: `MUTATION_APPLY_NOT_ENABLED` blocked surface 유지

### Future Paths

1. guarded live executor smoke evidence draft
   - 기대: explicit local-only guarded command에서 blocked top-level surface와 runtime sidecar evidence 동시 확인
   - 상태: next implementation

## Recommended Testing Order

다음 검증 순서는 아래로 고정한다.

1. default blocked-flow smoke 유지 확인
2. activation-on local-file candidate stub 유지 확인
3. explicit local-only opt-in smoke harness 정의
4. concrete executor skeleton smoke evidence 검증
5. top-level success promotion 규칙 정리
6. adapter-specific runtime failure taxonomy 검증
7. pre-execution audit/executor handoff seam 검증
8. fake/sandboxed executor smoke seam 검증
9. mutation apply executor router dry-run seam 검증
10. execution enablement checkpoint review
11. pre-side-effect executor router implementation draft 검증
12. top-level promotion router implementation draft 검증
13. execution enablement final checkpoint review
14. guarded live executor implementation draft 검증
15. guarded live executor smoke command draft 검증
16. guarded live executor smoke evidence draft 검증

## Open Testing Gaps

아직 남아 있는 테스트 갭:

1. guarded live executor smoke evidence capture
2. actual execution enablement 이후 smoke 업데이트 기준
3. real side-effect rollback drill 여부

## Notes

- 현재는 설계/contract 단계라서 전체 pytest나 live gate보다 타깃 mutation/runtime/smoke suite가 우선이다.
- 실제 execution을 열기 전까지는 default smoke가 계속 실패 아닌 “blocked success” 성격으로 유지되는 것이 맞다.

## Next Step

다음 작업은 `LOOP-067 V1.5 reindex live adapter guarded live executor smoke evidence draft`다. 이 문서는 이후 loop들의 테스트 상태/로드맵 기준 요약본으로 재사용한다.
