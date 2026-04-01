# Trunk RAG Version Roadmap

## Purpose
- `trunk_rag`의 현재 위치와 다음 버전의 방향을 버전 기준으로 고정한다.
- 현재 제품을 `V1`, 다음 제품을 `V2`, 장기 목표를 `V3`로 구분한다.
- 이후 문서/PR/릴리즈 노트에서 같은 버전 언어를 쓰도록 기준을 제공한다.

## Version Ladder

| version | product identity | core shape | primary goal |
| --- | --- | --- | --- |
| `V1` | `RAG product` | 인덱싱 + 질의 + 운영 통제 | 배포 가능한 로컬 웹 RAG MVP |
| `V2` | `Agent-enabled RAG` | RAG + tool/skill/middleware | 자동화 가능한 단일 에이전트 워크플로우 |
| `V3` | `Agent system` | planner/worker + MCP ecosystem | 다단계 작업 실행과 외부 시스템 연동 |

## Current Position

현재 `trunk_rag`는 `V1`이다.

- 핵심 기능:
  - 문서 인덱싱
  - 질의 응답
  - 업로드 요청
  - 관리자 승인/반려
  - 운영 게이트
- 핵심 가치:
  - 로컬 우선
  - 단일 실행 경로
  - 경량 런타임
  - 운영 예측 가능성
- 현재 해석:
  - `1. 인덱싱`
  - `2. 질의`
  - `3. 업로드 요청`
  - `4. 관리자 승인`
  - `5. 운영 게이트`
  중 `1~2`는 코어 RAG 기능이고, `3~5`는 운영/관리 레이어다.

## V1 Boundary

`V1`은 “에이전트”가 아니라 “운영 가능한 RAG 제품”이다.

### In
- Markdown 문서 기반 인덱싱/검색/질의
- 웹 UI(`intro -> app/admin`)
- 업로드 요청/승인 워크플로우
- runtime profile, fingerprint, `ops-baseline` 같은 운영 게이트
- 경량 로컬 스택(FastAPI + Chroma + 선택형 LLM)

### Out
- planner/worker 멀티에이전트
- 장기 상태를 가진 자율 작업 실행
- 복수 외부 시스템을 MCP로 연결한 tool mesh
- GraphRAG 통합
- 대규모 workflow orchestration

### V1 Exit Criteria
- 기본 설치/실행/복구 경로가 고정된다.
- `ops-baseline`과 all-routes 게이트가 운영 기준으로 유지된다.
- 업로드 요청/승인 경로가 운영자 기준으로 재현 가능하다.
- 기본 로컬 런타임(`ollama + llama3.1:8b + timeout 30s`)이 문서/게이트 기준으로 고정된다.

## V2 Boundary

`V2`는 기존 RAG 제품 위에 에이전트 레이어를 얹은 `Agent-enabled RAG`다.

핵심 변화는 “질문에 답한다”에서 “목표를 받고 필요한 도구를 선택해 여러 단계를 수행한다”로 옮겨가는 것이다.

### Required Additions
- `tool registry`
  - 내부 기능을 tool로 추상화
- `middleware chain`
  - auth, logging, budget, timeout, allowlist, audit
- `skill registry`
  - 작업별 프롬프트/워크플로우 묶음
- `execution state`
  - 어떤 tool을 어떤 순서로 썼는지 기록
- `agent runtime`
  - 입력을 받고 skill/tool 실행을 조합하는 단일 에이전트 런타임

### Still Out in V2
- planner/worker 다중 에이전트 분산 실행
- 복잡한 장기 메모리 시스템
- GraphRAG 본체 통합
- 대규모 외부 시스템 자동화

## V2 Architecture

### 1. Agent Runtime
- 새 요청 타입을 받는다.
- 질문 분류, skill 선택, tool 호출, 응답 합성을 담당한다.
- 현재 `/query`와 별개로 시작하거나, 추후 `/query` 상위 계층으로 둘 수 있다.

### 2. Middleware
- agent 실행 전후에 공통 정책을 적용한다.
- 최소 권장 미들웨어:
  - request id
  - runtime budget
  - tool allowlist
  - timeout/retry
  - audit log
  - unsafe action guard

### 3. Skill Registry
- 작업 유형별 preset을 둔다.
- 초기 후보:
  - `ops_check`
  - `doc_intake_review`
  - `compare_answer`
  - `admin_triage`

### 4. Tool Registry
- 기존 기능을 tool로 재노출한다.
- 1차 내부 tool 후보:
  - `search_docs`
  - `read_doc`
  - `list_collections`
  - `health_check`
  - `reindex`
  - `list_upload_requests`
  - `approve_upload_request`
  - `reject_upload_request`

### 5. State + Trace
- 실행 단계, tool 결과, 실패 사유를 구조화해 남긴다.
- 현재 `request_id`, runtime profile, budget trace를 agent trace로 확장하는 방향이 맞다.

### 6. MCP Boundary
- `V2`에서는 MCP를 “외부 도구 연결 표준”로 사용한다.
- 초기 방향:
  - 내부 tool registry는 그대로 유지
  - 외부 시스템 연결이 필요할 때만 MCP client를 붙인다
- 즉, `MCP first`가 아니라 `internal tools first, MCP second`가 원칙이다.

## Roadmap

### `V1.0` Current
- 배포 가능한 로컬 웹 RAG MVP
- 인덱싱/질의/업로드 승인/운영 게이트

### `V1.5` Agent-ready Runtime
- 내부 기능 tool abstraction 시작
- middleware 기본 체인 도입
- request/state/audit 구조 준비
- 아직 제품 정체성은 `RAG product`
- 실행 브랜치와 첫 작업 묶음은 `docs/V1_5_AGENT_READY_PLAN.md`를 따른다.

### `V2.0` Single Agent
- 단일 agent runtime 도입
- skill selector + tool registry + execution trace
- 운영 점검/문서 검토/비교 답변 같은 agent workflow 제공

### `V2.5` MCP-enabled Agent
- 외부 파일/DB/내부 시스템을 MCP로 연결
- 외부 도구 연결은 필요 최소한으로 유지

### `V3.0` Agent System
- planner/worker 또는 multi-agent
- 병렬 작업, 장기 작업, 다중 외부 시스템 orchestration

## Recommended Delivery Order

1. `V1` 안정화 유지
- 현재 운영 게이트를 깨지 않는다.

2. `V1.5`
- tool registry
- middleware
- state/audit

3. `V2.0`
- single-agent
- skill registry
- 내부 tool 기반 자동화

4. `V2.5`
- MCP 연결

5. `V3.0`
- multi-agent는 필요가 생긴 뒤에만

## Decision Rules

- `V1`에서는 제품 경량성과 운영 가능성을 우선한다.
- `V2`에서도 처음부터 멀티에이전트로 가지 않는다.
- `MCP`는 내부 기능 정리가 끝난 뒤 붙인다.
- `GraphRAG`, heavy rerank, 복잡한 orchestration은 `V2` 기본 범위에 넣지 않는다.
- 버전이 올라가도 `trunk_rag`의 기본 정체성은 “문서 중심 로컬 지식 시스템”에서 크게 벗어나지 않는다.
