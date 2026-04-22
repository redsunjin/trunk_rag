# V1.5 Reindex Live Adapter Pre-Side-Effect Executor Router Implementation Draft

작성일: 2026-04-22
Loop: `LOOP-062`
상태: 완료

## 결론

valid mutation apply 이후 actual `index_service.reindex()` side effect는 계속 닫아 둔 채, direct `_tool_reindex` handler로 내려가기 전에 mutation executor router dry-run이 실행되는 runtime seam을 코드와 테스트로 고정했다.

다음 단계는 executor sidecar를 future top-level apply success/failure surface로 승격하는 promotion router implementation draft다.

## 구현 내용

1. `services/tool_middleware_service.py`
   - `ToolExecutionState`에 `mutation_executor_result`, `mutation_success_promotion`, `mutation_apply_router_dry_run` state를 추가했다.
   - `_route_pre_side_effect_mutation_executor_dry_run()`을 추가해 blocked apply result 생성 후 direct tool handler 호출 전에 persisted audit record, append-only receipt, mutation execution request, executor router dry-run을 순서대로 수행한다.
   - `_attach_middleware_metadata()`는 pre-side-effect router가 만든 audit receipt/executor result/promotion/router dry-run evidence를 재사용해 double audit append와 double executor invocation을 피한다.

2. `services/mutation_executor_service.py`
   - `build_reindex_mutation_apply_router_dry_run_contract()`에 `route_location` 인자를 추가했다.
   - runtime pre-side-effect path는 `mutation_apply_guard_pre_side_effect_router`로, 기존 contract 기본값은 `blocked_result_metadata_enrichment`로 유지했다.

3. 테스트
   - middleware integration test가 valid apply 이후 direct reindex tool handler가 호출되지 않고 router dry-run evidence가 `mutation_apply_guard_pre_side_effect_router` 위치를 가리키는지 확인한다.
   - agent runtime test도 같은 router evidence가 error payload와 execution trace contract에 함께 남는지 확인한다.

## 유지 조건

- actual top-level apply success는 아직 열지 않는다.
- `mutation_executor_result`는 concrete skeleton stage에서도 blocked success sidecar로 유지한다.
- upload review live execution은 계속 `boundary_noop`로 둔다.
- public agent endpoint는 범위 밖이다.

## 검증

- `./.venv/bin/python -m pytest -q tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py`
  - 결과: `35 passed`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
  - 결과: ready
- `git diff --check`
  - 결과: 통과

## 다음 액션

`LOOP-063 V1.5 reindex live adapter top-level promotion router implementation draft`에서 actual side effect를 열지 않고 executor result/error sidecar의 top-level promotion seam을 구현 초안 수준으로 고정한다.
