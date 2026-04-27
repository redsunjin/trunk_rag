# V1.5 Reindex Live Adapter Guarded Live Executor Implementation Draft

작성일: 2026-04-22
Loop: `LOOP-065`
상태: 완료

## 결론

actual top-level apply enablement는 계속 닫아 둔 채, explicit local-only binding stage로만 도달 가능한 guarded live executor seam을 구현했다.

새 stage는 `binding_stage=guarded_live_executor`이며, 이 stage에서만 `index_service.reindex()` 호출 seam이 열린다. 기본 path, `candidate_stub`, `live_binding_stub`, `concrete_executor_skeleton` stage는 기존 동작을 유지한다.

## 구현 내용

1. `services/mutation_executor_service.py`
   - `REINDEX_LIVE_ADAPTER_BINDING_STAGE_GUARDED_LIVE_EXECUTOR`를 추가했다.
   - `ReindexGuardedLiveMutationExecutor`를 추가해 explicit guarded stage에서 `index_service.reindex()`를 호출한다.
   - executor contract에는 `actual_runtime_handler=index_service.reindex`, `actual_runtime_handler_invoked=true` evidence를 남긴다.
   - runtime result는 `mutation_executor_result.runtime_result`와 `reindex_summary.runtime_*` fields로 요약된다.

2. middleware path
   - direct `_tool_reindex` handler는 여전히 호출하지 않는다.
   - guarded executor result는 기존 blocked apply surface의 sidecar로 남고, `mutation_success_promotion` 및 `mutation_top_level_promotion_router` evidence와 이어진다.

3. 테스트
   - executor unit test는 `index_service.reindex()`를 monkeypatch해 guarded stage에서만 호출되는지 확인한다.
   - middleware integration test는 direct tool handler bypass와 guarded executor sidecar/promotion evidence를 함께 확인한다.

## 유지 조건

- current top-level runtime은 계속 `ok=false`, `error.code=MUTATION_APPLY_NOT_ENABLED`다.
- default/public route에서 actual side effect는 열지 않는다.
- concrete skeleton smoke는 계속 side effect 없는 blocked-success evidence다.
- upload review live execution은 범위 밖이다.

## 검증

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_middleware_service.py tests/test_agent_runtime_service.py tests/test_smoke_agent_runtime.py`
  - 결과: `55 passed`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
  - 결과: ready
- `git diff --check`
  - 결과: 통과

## 다음 액션

`LOOP-066 V1.5 reindex live adapter guarded live executor smoke command draft`에서 smoke harness가 guarded stage를 명시적으로 선택할 수 있게 하되, default smoke와 concrete skeleton smoke는 계속 side effect 없는 경로로 유지한다.
