# V1.5 Reindex Live Adapter Top-Level Promotion Router Implementation Draft

작성일: 2026-04-22
Loop: `LOOP-063`
상태: 완료

## 결론

actual `index_service.reindex()` side effect를 열지 않고, executor success/failure sidecar를 future top-level apply success/failure surface로 옮기는 deterministic promotion router draft evidence를 코드와 테스트로 고정했다.

current runtime은 계속 `ok=false`, `error.code=MUTATION_APPLY_NOT_ENABLED` blocked surface를 유지한다. `top_level_promotion_enabled=false`, `actual_side_effect_enabled=false`다.

## 구현 내용

1. `services/mutation_executor_service.py`
   - `v1.5.reindex_live_adapter_top_level_promotion_router.v1` schema constant와 `build_reindex_top_level_promotion_router_contract()`를 추가했다.
   - success route는 `error.mutation_executor_result` sidecar를 future top-level `result`로 옮기는 조건과 preview payload를 남긴다.
   - failure route는 adapter-specific failure taxonomy codes를 future top-level `error` surface로 옮기는 target을 남긴다.

2. `services/tool_middleware_service.py`
   - blocked apply metadata에 `mutation_top_level_promotion_router`를 추가하고 execution trace contracts에도 같은 evidence를 남긴다.
   - pre-side-effect executor router가 만든 executor result와 success promotion evidence를 재사용한다.

3. `scripts/smoke_agent_runtime.py`
   - concrete opt-in smoke summary에 top-level promotion router evidence를 요약한다.

## 유지 조건

- top-level apply success/failure는 아직 실제 runtime 응답으로 승격하지 않는다.
- direct `_tool_reindex`와 `index_service.reindex`는 계속 호출하지 않는다.
- upload review live execution은 계속 `boundary_noop`로 둔다.
- public agent endpoint는 범위 밖이다.

## 검증

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py`
  - 결과: `53 passed`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
  - 결과: ready
- `git diff --check`
  - 결과: 통과

## 다음 액션

`LOOP-064 V1.5 reindex live adapter execution enablement final checkpoint review`에서 actual execution gate를 열 수 있는지 재판정한다.
