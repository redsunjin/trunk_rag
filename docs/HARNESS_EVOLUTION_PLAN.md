# Harness Evolution Plan

## Purpose
- 버전이 바뀔 때 하네스도 같이 바뀌어야 한다는 원칙을 `trunk_rag` 기준으로 고정한다.
- `V1`, `V1.5`, `V2`, `V3`가 어떤 하네스 모드를 가져야 하는지 정의한다.
- 이후 `NEXT_SESSION_PLAN.md`와 `roadmap_harness.py`가 읽을 최소 메타데이터 계약을 제공한다.

## Core Rule
- 하네스는 제품 목적에 종속된다.
- 따라서 버전이 바뀌면 하네스도 그대로 두지 않고, 그 버전의 목적에 맞게 확장 또는 재구성해야 한다.
- 다만 이전 버전 하네스를 버리는 것이 아니라, 상위 레이어를 추가하는 방식으로 진화시키는 것이 기본 원칙이다.

## Version To Harness Mapping

| version | harness mode | primary job | main evaluator |
| --- | --- | --- | --- |
| `V1` | `v1_operating_loop` | 운영 가능한 웹 RAG MVP 유지 | `ops-baseline`, runtime preflight, release gate |
| `V1.5` | `v1_5_agent_ready_loop` | `V2` 준비용 내부 구조 하드닝 | structure checks, tool/middleware/trace contract checks |
| `V2` | `v2_single_agent_loop` | 단일 agent runtime 품질/안전성 관리 | tool trace, skill workflow eval, safety checks |
| `V3` | `v3_agent_system_loop` | multi-agent / MCP orchestration 제어 | orchestration recovery, long-run eval, external tool safety |

## Current Interpretation

현재 저장소는 공식적으로 `V1`이다.

- 공식 active loop:
  - `LOOP-001`
  - `v1_operating_loop`
- 현재 feature branch:
  - `feature/v1.5-agent-ready-runtime`
  - 준비 목적의 `v1_5_agent_ready_loop` 문서/설계 작업

즉 현재는 "`V1` 공식 운영 하네스 유지 + `V1.5` 하네스 준비"의 중첩 상태다.

## Required Session Harness Metadata

앞으로 `NEXT_SESSION_PLAN.md`의 `Session Loop Harness`에는 아래 값을 최소한 유지한다.

- `current_active_id`
- `current_active_title`
- `current_version_track`
- `current_harness_mode`
- `session_start_command`
- `default_regression_gate`
- `branch_execution_policy`
- `branch_plan_doc`
- `closeout_rule`
- `blocked_rule`
- `promotion_rule`

## Field Semantics

### `current_version_track`
- 현재 공식 제품 단계
- 예:
  - `V1`
  - `V1.5`
  - `V2`
  - `V3`

### `current_harness_mode`
- 현재 하네스의 운영 모드
- 허용값:
  - `v1_operating_loop`
  - `v1_5_agent_ready_loop`
  - `v2_single_agent_loop`
  - `v3_agent_system_loop`

### `branch_execution_policy`
- 브랜치가 공식 active loop를 자동 대체하는지 여부
- 현재 권장값:
  - `non-main branches do not override official active loop without explicit redirect or queue promotion`

### `branch_plan_doc`
- 브랜치 전용 작업 기준 문서
- 없으면 `-`
- 있으면 repo 상대 경로를 적는다

## Mode Definitions

### `v1_operating_loop`
- 목표:
  - 배포 가능한 웹 MVP 운영 유지
- 중심 아티팩트:
  - `TODO.md`
  - `NEXT_SESSION_PLAN.md`
  - `scripts/check_ops_baseline_gate.py`
  - `scripts/runtime_preflight.py`
- 중심 evaluator:
  - `ops-baseline`
  - `/health`
  - all-routes readiness

### `v1_5_agent_ready_loop`
- 목표:
  - `V2`로 넘어가기 위한 구조 준비
- 중심 아티팩트:
  - `docs/V1_5_AGENT_READY_PLAN.md`
  - `docs/HARNESS_MASTER_GUIDE.md`
  - branch-specific work package docs
- 중심 evaluator:
  - tool registry contract checks
  - middleware skeleton checks
  - execution trace contract checks
  - 기존 `V1` 회귀 게이트 유지

### `v2_single_agent_loop`
- 목표:
  - 단일 agent runtime의 도구 선택, workflow 품질, 안전성 관리
- 중심 evaluator:
  - tool execution trace
  - workflow pass/fail fixtures
  - unsafe action guard
  - route/tool reason observability

### `v3_agent_system_loop`
- 목표:
  - multi-agent / MCP orchestration 제어
- 중심 evaluator:
  - multi-step recovery
  - external tool contract
  - long-running task stability
  - orchestration observability

## Transition Rules

### `V1 -> V1.5`
- 공식 제품은 여전히 `V1`
- feature branch에서 `v1_5_agent_ready_loop` 문서와 구조를 먼저 준비
- `V1` active loop와 충돌하지 않게 유지

### `V1.5 -> V2`
- 내부 tool / middleware / trace 계약이 준비되면
- 공식 `current_version_track`을 `V2`로 올리고
- `current_harness_mode`를 `v2_single_agent_loop`로 바꾼다

### `V2 -> V3`
- planner/worker, MCP orchestration, external tool safety가 실제 제품 범위가 될 때만 전환한다

## Adoption Checklist
1. 새 버전 목표를 먼저 문서화한다.
2. 그 버전에 맞는 `harness mode`를 정한다.
3. `NEXT_SESSION_PLAN.md`의 `Session Loop Harness` 메타데이터를 갱신한다.
4. `roadmap_harness.py`가 그 메타데이터를 검증하도록 만든다.
5. 새 버전에서 중요한 evaluator를 추가한다.

## Current Recommendation
- 지금 당장 공식 모드는 계속 `V1 / v1_operating_loop`
- 동시에 `V1.5` 준비 브랜치에서는 다음을 진행
  1. `tool registry`
  2. `middleware chain`
  3. `execution trace`
  4. `agent entry`
- 각 단계마다 `Harness Worksheet`를 붙여 문서/검증/가드레일을 함께 남긴다
