# V1.5 Agent-ready Runtime Plan

## Purpose
- `V1` 운영 기준선을 유지한 채 `V2`로 넘어가기 위한 준비 작업을 분리한다.
- `trunk_rag`의 다음 단계는 곧바로 agent product로 점프하지 않고, 먼저 `agent-ready runtime`을 만든다.
- 이 문서는 `V1.5` 준비 트랙의 운영 원칙, 범위, 첫 구현 순서를 고정한다.
- 하네스 설계 원칙과 워크북 템플릿은 `docs/HARNESS_MASTER_GUIDE.md`를 따른다.
- 버전별 하네스 모드와 세션 메타데이터 계약은 `docs/HARNESS_EVOLUTION_PLAN.md`를 따른다.

## Branch Strategy
- 안정 기준선: `main`
- `V1.5`는 장기 브랜치명이 아니라 버전 준비 트랙이다.
- 실제 구현은 최신 `main`에서 분기한 짧은 작업 브랜치로 진행한다.
- 머지 후 작업 브랜치는 삭제하고, 다음 단계도 다시 최신 `main`에서 새로 분기한다.

원칙:
- `main`은 `V1` 안정화와 소규모 hotfix만 받는다.
- `V1.5` 준비 작업은 `main`을 더럽히지 않는 짧은 작업 브랜치에서 진행한다.
- 운영 중 발견된 `V1` 오류 수정은 별도 `hotfix/v1.0.x-*` 브랜치에서 처리한다.
- 이 브랜치는 `TODO.md`의 최상위 `active`를 자동으로 대체하지 않는다. 일반적인 `진행` 요청은 계속 공식 `active` 루프를 따른다.
- 따라서 `V1.5` 작업은 사용자가 해당 준비 작업을 명시적으로 지시했을 때만 직접 진행한다.

## Product Position
- 현재 제품: `V1 = RAG product`
- 현재 목표: `V1`을 깨지 않고 `V2`를 위한 내부 구조를 준비
- 이번 단계 결과물: 여전히 `RAG product`

즉, `V1.5`는 새 제품 출시가 아니라 내부 구조 준비 단계다.

## Scope

### In
- 기존 기능을 internal tool로 추상화할 준비
- 공통 `middleware chain` 초안 도입
- request 단위 `execution trace` 구조 정의
- agent runtime이 얹힐 자리와 계약 정의

### Out
- 최종 단일 agent product 출시
- skill 자동 선택 로직 전체 구현
- MCP client/server 통합
- planner/worker 멀티에이전트
- GraphRAG 재개

## First Work Packages

### WP1. Internal Tool Registry Skeleton
- 기존 기능을 그대로 유지한 채 tool registry 인터페이스를 만든다.
- 1차 후보:
  - `search_docs`
  - `read_doc`
  - `list_collections`
  - `health_check`
  - `reindex`
  - `list_upload_requests`
  - `approve_upload_request`
  - `reject_upload_request`

완료 기준:
- tool definition schema가 생긴다.
- 기존 service 호출을 감싸는 thin adapter가 생긴다.
- 기존 `/query` 기본 경로를 깨지 않는다.

진행 상태 (2026-04-10):
- `services/tool_registry_service.py`에 `ToolDefinition`, `ToolContext`, `RegisteredTool`, `invoke_tool()` skeleton을 추가했다.
- 1차 등록 tool은 `search_docs`, `read_doc`, `list_collections`, `health_check`, `reindex`, `list_upload_requests`, `approve_upload_request`, `reject_upload_request`다.
- `search_docs`는 LLM 호출 없이 기존 collection routing과 context builder를 감싸고, `read_doc`는 seed/managed active markdown을 읽는다.
- `reindex`와 upload approval 계열처럼 쓰기 부작용이 있는 tool은 `ToolContext.allow_mutation=True`가 없으면 실행하지 않는다.
- upload 승인/반려 로직은 API route 전용 helper에서 service 함수로 이동해 endpoint와 tool adapter가 같은 경로를 사용한다.

### WP2. Middleware Chain Skeleton
- tool/runtime 실행 전후에 공통 정책을 넣을 수 있는 체인을 추가한다.
- 1차 미들웨어:
  - request id
  - timeout budget
  - tool allowlist
  - audit log
  - unsafe action guard

완료 기준:
- 미들웨어를 순차 적용할 수 있는 최소 실행기 구조가 생긴다.
- 기존 runtime profile/budget 정보가 미들웨어 입력으로 연결된다.

진행 상태 (2026-04-10):
- `services/tool_middleware_service.py`에 `invoke_tool_with_middlewares()`와 `DEFAULT_TOOL_MIDDLEWARES`를 추가했다.
- 기본 체인은 `request_id`, `timeout_budget`, `tool_allowlist`, `unsafe_action_guard`, `audit_log` 순서로 실행된다.
- `ToolContext.timeout_seconds`를 추가해 runtime budget 입력을 tool adapter 호출 context까지 전달한다.
- 쓰기 tool은 middleware의 unsafe action guard에서 먼저 차단되며, 기존 `ToolContext.allow_mutation` guard도 registry adapter에 그대로 남겨 이중 안전장치를 유지한다.
- 실행 결과에는 `middleware.request_id`, `timeout_seconds`, `allowed_tools`, `trace`, `audit_log`가 포함된다.

### WP3. Execution Trace Contract
- 한 요청에서 어떤 단계와 tool이 실행됐는지 구조적으로 남긴다.
- 현재 `request_id`, runtime profile, route reason, budget profile을 trace seed로 사용한다.

완료 기준:
- trace schema가 고정된다.
- tool 실행 결과와 실패 원인이 trace에 남는다.

진행 상태 (2026-04-10):
- `services/tool_trace_service.py`에 `TRACE_SCHEMA_VERSION = "v1.5.tool_execution_trace.v1"`와 `build_execution_trace()`를 추가했다.
- `services/tool_middleware_service.py`의 결과에 기존 `middleware` metadata와 별도로 `execution_trace`를 추가했다.
- trace는 `request_id`, `actor`, `runtime`, `policy`, `tool`, `routing`, `middleware`, `outcome`, `audit`를 최상위 필드로 고정한다.
- `search_docs` 결과의 `query_profile`, `collections`, `route_reason`, `budget_profile`은 `routing` seed로 들어간다.
- middleware 차단은 `middleware.blocked_by`와 `outcome.error.code`에 함께 남는다.

### WP4. Agent Runtime Entry Draft
- 기존 `/query`를 대체하지 않고 별도 실험 엔트리로 시작한다.
- 예: `/agent/query` 또는 내부 service entry

완료 기준:
- 단일 입력을 받아 tool call 흐름을 테스트할 수 있다.
- 실제 사용자 기본 경로는 계속 `/query`다.

진행 상태 (2026-04-10):
- `services/agent_runtime_service.py`에 `AgentRuntimeRequest`와 `run_agent_entry()`를 추가했다.
- 기본 entry는 단일 `input`을 `search_docs` payload로 바꾸고 `tool_middleware_service.invoke_tool_with_middlewares()`를 호출한다.
- 기본 allowlist는 read-only tool(`search_docs`, `read_doc`, `list_collections`, `health_check`, `list_upload_requests`)로 제한한다.
- 명시 tool/payload는 전달하되, write tool은 기본 allowlist와 mutation guard를 통과하지 못한다.
- 결과는 `entry`, `tool_call`, `execution_trace`, `error`를 포함하고, 사용자 기본 `/query` 경로는 변경하지 않는다.

## Integration Review
- 2026-04-10 통합 검토는 `docs/reports/V1_5_AGENT_READY_RUNTIME_REVIEW_2026-04-10.md`에 기록했다.
- 결론은 `main` 병합 후 검증 통과다. post-merge 기준 full regression과 live `generic-baseline` gate를 재실행했다.
- WP1-WP4는 모두 내부 service 경계로 추가됐고, 사용자 기본 `/query` 계약은 변경하지 않았다.

## Follow-up Policy
- 2026-04-10 후속 정책 판단은 `docs/reports/V1_5_FOLLOWUP_POLICY_2026-04-10.md`에 기록했다.
- public `/agent/*` API는 지금 열지 않는다.
- `execution_trace` persistence는 redaction/storage/retention 정책이 생길 때까지 보류한다.
- agent runtime 기본 allowlist는 read-only tool로 유지한다.
- trace redaction 정책 초안은 `docs/reports/V1_5_TRACE_REDACTION_POLICY_2026-04-10.md`에 기록했다.
- actor별 allowlist/mutation source 초안은 `docs/reports/V1_5_ACTOR_ALLOWLIST_POLICY_SOURCE_2026-04-11.md`에 기록했다.
- preview payload/persisted audit contract는 `docs/reports/V1_5_PREVIEW_AUDIT_CONTRACT_2026-04-12.md`에 기록했다.
- preview seed helper/append-only audit sink skeleton은 `docs/reports/V1_5_PREVIEW_SEED_AUDIT_SINK_2026-04-12.md`에 기록했다.
- `config/actor_policy_manifest.json` + `services/actor_policy_service.py` 기준 actor policy resolver가 추가돼 runtime/middleware가 actor category별 read allowlist와 mutation candidate metadata를 읽는다.
- `services/tool_middleware_service.py`는 `mutation_policy_guard`를 통해 mutation candidate write를 `ADMIN_AUTH_REQUIRED` -> `MUTATION_INTENT_REQUIRED` -> `PREVIEW_REQUIRED` 순서로 차단하고, `services/agent_runtime_service.py`는 `admin_code`/`mutation_intent` presence를 entry metadata에 남긴다.
- `services/tool_trace_service.py`는 `build_preview_contract()`와 `build_persisted_audit_record()`로 preview/audit contract를 순수 함수로 고정하고, `PREVIEW_REQUIRED` 응답과 execution trace contract seed에 이를 포함한다.
- `services/tool_preview_service.py`는 contract를 실제 preview seed로 채우고, `services/tool_audit_sink_service.py`는 persisted record만 받는 append-only sink protocol/null-memory sink를 제공한다.
- `services/tool_apply_service.py`는 preview-confirmed mutation apply envelope draft와 validation error taxonomy를 제공하고, `services/tool_middleware_service.py`는 `mutation_apply_guard`로 preview-confirmed apply path를 `MUTATION_APPLY_NOT_ENABLED`까지 차단한다.
- `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md`는 실제 execution `No-Go`, local append-only backend/retention/operator activation 조건, `reindex` 우선 live scope를 고정했다.
- `docs/reports/V1_5_MUTATION_EXECUTOR_INTERFACE_DRAFT_2026-04-18.md`는 `MutationExecutionRequest`, `NoopMutationExecutor`, `ReindexMutationExecutorAdapter`, `mutation_executor` contract seed를 고정했다.
- `docs/reports/V1_5_DURABLE_MUTATION_AUDIT_BACKEND_SKELETON_2026-04-18.md`는 default null sink 유지, `local_file_append_only` opt-in, `90일 rolling_window`, stable `sequence_id` receipt를 고정했다.
- `docs/reports/V1_5_REINDEX_EXECUTOR_ACTIVATION_SEAM_DRAFT_2026-04-18.md`는 `reindex` activation guard, noop fallback, candidate stub selection contract를 고정했다.
- `docs/reports/V1_5_UPLOAD_REVIEW_EXECUTOR_BOUNDARY_REVIEW_2026-04-18.md`는 upload review execution을 `boundary_noop` selection과 rollback/audit/document binding precondition으로 분리했다.
- `docs/reports/V1_5_MUTATION_AUDIT_RETENTION_OPS_DRAFT_2026-04-18.md`는 `90일 rolling_window`, explicit local-operator prune ownership, nested `ops` receipt contract를 고정했다.
- `docs/reports/V1_5_REINDEX_LIVE_READINESS_CHECKLIST_DRAFT_2026-04-19.md`는 `reindex` live enablement 전 필요한 checklist/evidence 항목을 고정했다.
- `docs/reports/V1_5_MUTATION_ACTIVATION_SMOKE_EVIDENCE_2026-04-19.md`는 blocked flow smoke output을 readiness evidence와 `mutation_executor` summary 기준으로 고정했다.
- `docs/reports/V1_5_REINDEX_ACTIVATION_CHECKPOINT_REVIEW_2026-04-19.md`는 default blocked path와 activation-on local-file candidate stub path를 함께 점검해 live enablement verdict를 다시 `No-Go`로 고정했다.
- `docs/reports/V1_5_REINDEX_ACTIVATION_OPERATOR_RUNBOOK_DRAFT_2026-04-19.md`는 baseline smoke, activation-on local-file smoke, audit receipt 확인, deactivation, abort condition을 local operator 절차로 고정했다.
- 다음 구현은 `LOOP-046 reindex live adapter success contract draft`이며, 이 단계에서는 `LOOP-045`에서 고정한 verification matrix를 기준으로 future success/failure result shape와 error taxonomy를 draft 수준으로 정리한다.
- raw input, retrieved context, document content, local path, admin code, credential은 저장/노출 기본 대상에서 제외한다.
- `services/tool_trace_service.py`는 `redact_execution_trace()`로 `internal`, `public`, `persisted` audience별 trace 정규화를 제공한다.

## Suggested Order
1. `WP1` tool registry skeleton
2. `WP2` middleware chain skeleton
3. `WP3` execution trace contract
4. `WP4` agent runtime entry draft

## Validation Rules
- `V1` 회귀 게이트를 항상 유지한다.
- 기본 검증:
  - `./.venv/bin/python -m pytest -q`
  - `./.venv/bin/python scripts/roadmap_harness.py validate`
- `V1.5` 새 구조는 가능한 한 기존 API 계약을 깨지 않는 방식으로 추가한다.

## Exit Criteria
- 내부 tool registry가 최소 1차 범위 기능을 감싼다.
- middleware chain이 최소 정책(request id, timeout, allowlist, audit)을 적용할 수 있다.
- execution trace 구조가 고정된다.
- 이후 `V2`에서 단일 agent runtime을 얹을 수 있는 안정된 진입점이 생긴다.
