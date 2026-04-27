# V1.5 Reindex Live Adapter Enablement Go/No-Go Review - 2026-04-21

## Summary

`reindex` live adapter actual execution enablement 판정은 `No-Go`다. success promotion과 failure taxonomy contract는 준비됐지만, 현재 middleware에서 `mutation_apply_guard`를 열면 durable audit receipt와 explicit live adapter binding을 pre-execution 단계에서 강제하지 못하고 기존 tool handler가 곧바로 `index_service.reindex()`를 호출할 수 있다.

다음 단계는 actual side effect를 여는 구현이 아니라, pre-execution audit receipt와 mutation executor handoff seam을 먼저 고정하는 것이다.

## Verdict

- actual execution enablement: `No-Go`
- next planning step: `Go` for pre-execution audit/executor handoff seam draft
- first live tool scope remains: `reindex` only
- default/public surface: closed
- upload review live execution: excluded

## Evidence Reviewed

1. `mutation_apply_guard_middleware`
   - valid apply envelope도 현재 `MUTATION_APPLY_NOT_ENABLED`로 blocked result를 만든다.
   - 이 blocked result가 있어야 `_attach_middleware_metadata()`가 persisted audit receipt를 만들고 `mutation_executor_service.execute_mutation_request()` sidecar를 붙인다.
2. `tool_registry_service._tool_reindex`
   - middleware가 block하지 않으면 기존 tool adapter는 곧바로 `index_service.reindex()`를 호출한다.
3. `index_service.reindex`
   - 실제 Chroma/index runtime state를 재생성하는 side effect 경로다.
4. Existing contracts
   - `mutation_success_promotion`은 current blocked-success sidecar와 future top-level success surface mapping을 고정했다.
   - failure taxonomy helper는 future top-level failure surface mapping을 고정했다.

## Blockers

1. pre-execution durable audit handoff가 없다.
   - 현재 durable audit receipt는 blocked result metadata enrichment 과정에서 생긴다.
   - actual execution을 허용하면 side effect 전에 receipt를 강제하는 구조가 아니다.
2. mutation executor가 actual side effect path를 소유하지 않는다.
   - current concrete skeleton은 `MUTATION_APPLY_NOT_ENABLED` sidecar로만 실행된다.
   - guard를 열면 `mutation_executor_service`가 아니라 `tool_registry_service._tool_reindex`가 실제 write를 수행할 수 있다.
3. success/failure top-level surface 전환 지점이 아직 middleware runtime에 없다.
   - contract는 준비됐지만, `executor_result -> top-level result` 및 `executor_error -> top-level error` router가 없다.
4. smoke harness가 real side effect isolation을 검증하지 않는다.
   - concrete smoke는 skeleton evidence를 확인하지만 real index mutation을 sandboxed/fake executor로 검증하지 않는다.

## Required Before Go

actual execution enablement 전에 최소 아래가 필요하다.

1. `mutation_apply_guard`가 direct tool invocation을 열지 않고 mutation executor router로 넘기는 구조
2. side effect 이전에 durable local audit receipt를 생성/검증하는 pre-execution handoff
3. explicit live adapter binding이 없으면 actual executor를 선택할 수 없는 guard
4. fake/sandboxed executor 기반 success/failure smoke
5. top-level success/failure promotion을 middleware result로 변환하는 deterministic router
6. default smoke가 계속 blocked path를 유지한다는 회귀 검증

## Decision

`LOOP-057` 결론은 `No-Go`로 닫는다. 다음 loop는 `LOOP-058 V1.5 reindex live adapter pre-execution handoff seam draft`로 진행한다.

이 다음 loop에서도 actual `index_service.reindex()` side effect를 열지 않는다. 목표는 durable audit receipt, executor selection, top-level result/error promotion이 side effect 이전에 한 흐름으로 묶이는 seam을 테스트 가능한 계약으로 고정하는 것이다.

## Validation

- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready` (`active_id=LOOP-058`)
- `git diff --check` -> pass
