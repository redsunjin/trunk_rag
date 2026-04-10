# V1.5 Agent-ready Runtime Review - 2026-04-10

## Scope

- 대상 루프: `LOOP-021 V1.5 agent-ready runtime 통합 검토/병합 준비`
- 대상 브랜치: `feature/loop-017-tool-registry-skeleton`
- 기준선: `v1.0.1` 이후 `main`에서 분기한 V1.5 준비 브랜치
- 목적: WP1-WP4 결과를 병합 준비 관점으로 검토하고, V1 API 회귀 없이 내부 agent-ready runtime 기반이 들어갈 수 있는지 판단한다.

## Work Package Summary

| WP | 구현 결과 | 대표 파일 | 상태 |
| --- | --- | --- | --- |
| WP1 internal tool registry | 기존 RAG/collection/upload 기능을 internal tool adapter로 감쌌다. | `services/tool_registry_service.py` | 완료 |
| WP2 middleware chain | request id, timeout budget, allowlist, audit log, unsafe action guard를 순차 적용한다. | `services/tool_middleware_service.py` | 완료 |
| WP3 execution trace | tool/middleware 실행 결과를 `v1.5.tool_execution_trace.v1` schema로 고정한다. | `services/tool_trace_service.py` | 완료 |
| WP4 runtime entry draft | 단일 입력을 read-only allowlist 기반 single-tool 흐름으로 실행한다. | `services/agent_runtime_service.py` | 완료 |

## Commit Summary

```text
e2b1ba5 feat(agent): add internal tool registry skeleton
8897b6c feat(agent): add tool middleware chain skeleton
5dbbb79 feat(agent): add tool execution trace contract
21e8f7f feat(agent): add internal runtime entry draft
```

## Contract Review

### Preserved V1 Surface

- 기존 `/query`, `/health`, `/collections`, upload/admin endpoint 계약은 직접 변경하지 않았다.
- `search_docs` tool은 LLM 호출 없이 기존 collection routing과 context builder를 감싼다.
- 사용자 기본 `/query`는 여전히 기존 query route와 response shape를 사용한다.
- write 계열 tool은 기존 service 로직을 재사용하되, agent runtime 기본 allowlist에서는 제외된다.

### Internal Runtime Boundary

- `tool_registry_service.invoke_tool()`은 adapter 실행과 기존 mutation guard를 담당한다.
- `tool_middleware_service.invoke_tool_with_middlewares()`는 policy 실행, audit metadata, execution trace 생성을 담당한다.
- `tool_trace_service.build_execution_trace()`는 runtime/tool/routing/policy/outcome/audit trace 계약을 단일 schema로 묶는다.
- `agent_runtime_service.run_agent_entry()`는 아직 public API가 아니라 내부 service draft다.

### Safety Controls

- write side-effect tool은 `ToolContext.allow_mutation=True` 없이는 registry에서 차단된다.
- middleware의 `unsafe_action_guard`가 write tool을 먼저 차단해 이중 안전장치를 제공한다.
- agent runtime 기본 allowlist는 read-only tool로 제한된다.
- 명시 tool/payload 실행은 가능하지만 기본 allowlist를 넘지 못하면 `TOOL_NOT_ALLOWED`로 실패한다.

## Verification History

### LOOP-017

```text
tool registry + upload API: 13 passed
adjacent API/service: 73 passed
full regression: 146 passed
live gate: ready, generic-baseline 3/3 pass, avg_weighted_score=0.9467, p95_latency_ms=10807.335
roadmap_harness.py validate: ready
```

### LOOP-018

```text
middleware + tool registry: 10 passed
full regression: 151 passed
live gate: ready, generic-baseline 3/3 pass, avg_weighted_score=0.9467, p95_latency_ms=13232.923
roadmap_harness.py validate: ready
```

### LOOP-019

```text
trace + middleware + tool registry: 13 passed
full regression: 154 passed
live gate: ready, generic-baseline 3/3 pass, avg_weighted_score=0.9467, p95_latency_ms=12578.583
roadmap_harness.py validate: ready
```

### LOOP-020

```text
agent runtime + trace/middleware: 12 passed
full regression: 158 passed
live gate: ready, generic-baseline 3/3 pass, avg_weighted_score=0.9467, p95_latency_ms=9962.081
roadmap_harness.py validate: ready
```

### LOOP-021 Integration Review

```text
full regression: 158 passed
live gate: ready, generic-baseline 3/3 pass, avg_weighted_score=0.9467, p95_latency_ms=12089.431
roadmap_harness.py validate: ready
git diff --check: pass
```

## Merge Readiness

결론: 조건부 merge-ready.

근거:
- 신규 기능은 내부 service와 unit test 중심으로 추가됐고 public V1 API를 대체하지 않는다.
- full regression과 live `generic-baseline`이 각 루프에서 유지됐다.
- write action은 registry guard, middleware guard, agent runtime read-only allowlist로 방어된다.
- 문서 기준 `TODO.md`, `NEXT_SESSION_PLAN.md`, `README.md`, `SPEC.md`, `docs/V1_5_AGENT_READY_PLAN.md`가 V1.5 준비 상태를 반영한다.

조건:
- merge 직전에 최신 `main`을 가져와 충돌 여부를 확인한다.
- merge 대상 기준에서 full regression과 live gate를 다시 실행한다.
- 현재 브랜치의 이름은 `loop-017` 중심이지만 내용은 `LOOP-017`부터 `LOOP-020`까지 포함하므로, merge description에는 실제 포함 범위를 명시한다.

## Risks

- `agent_runtime_service.py`는 아직 public API가 아니므로 외부 사용자가 호출할 안정 계약으로 간주하면 안 된다.
- `execution_trace` schema는 V1.5 내부 계약이며, V2에서 public API로 승격하려면 별도 versioning 정책이 필요하다.
- `search_docs`는 context retrieval만 수행하고 answer generation은 하지 않는다. 이를 사용자 응답으로 오해하면 UX 혼선이 생긴다.
- write tool은 안전장치가 있지만, 향후 allowlist를 넓힐 때 admin auth, audit persistence, dry-run 정책이 추가로 필요하다.

## Follow-up Candidates

1. merge preparation: 최신 `main` rebase/merge 검토 후 post-merge full regression과 live gate 재실행
2. internal agent API draft: public `/query`와 분리된 `/agent/*` 실험 endpoint 여부 결정
3. trace persistence: 현재 in-memory response metadata인 trace를 파일/DB audit log로 남길지 결정
4. allowlist policy: actor별 allowlist와 mutation policy를 설정 파일 또는 admin policy로 분리
5. V2 planning: skill registry, planner, MCP는 이 브랜치 밖의 후속 트랙으로 유지

## Conclusion

V1.5 WP1-WP4는 기존 V1 제품 경계를 깨지 않는 내부 구조 준비로 완료됐다. 현재 브랜치는 `agent-ready runtime`의 최소 기반을 포함하며, 최신 `main` 기준 재검증을 조건으로 병합 준비 단계에 들어갈 수 있다.
