# Harness Master Guide

## Purpose
- `trunk_rag`에서 하네스를 "에이전트가 장기 작업을 일관되게 수행하도록 돕는 제어 시스템"으로 정의한다.
- 외부 글의 원칙을 현재 프로젝트에 맞는 실무 기준으로 재구성한다.
- 이 문서는 세 가지 용도를 동시에 가진다.
  - 재사용 가능한 하네스 설계 마스터 가이드
  - 새 작업에 붙일 워크북/템플릿
  - 현재 `trunk_rag` 하네스 구조 심사 결과

## Source Inputs
- Anthropic: https://www.anthropic.com/engineering/harness-design-long-running-apps
- OpenAI: https://openai.com/ko-KR/index/harness-engineering/

이 문서는 위 두 글의 핵심을 그대로 복제하지 않고, 현재 저장소 운영 방식에 맞게 재구성한다.

## What "Harness" Means Here

`trunk_rag`에서 하네스는 단순 테스트 모음이 아니다.

하네스는 아래를 묶는 운영 구조다.
- 무엇을 지금 해야 하는지 정하는 우선순위 구조
- 어떤 상태를 기록 시스템으로 남길지 정하는 문서 구조
- 무엇이 통과/실패인지 정하는 검증 구조
- 에이전트가 어디까지 자율적으로 움직일지 정하는 가드레일
- 드리프트가 생겼을 때 어떻게 정리할지 정하는 유지보수 루프

즉, 하네스는 `작업 선택 + 실행 규칙 + 검증 + 정리`의 묶음이다.

## Distilled Principles

### 1. 계획은 대화가 아니라 버전화된 아티팩트여야 한다
- Anthropic 글은 sprint contract처럼 "무엇을 만들고 어떻게 검증할지"를 먼저 합의하는 구조를 강조한다.
- OpenAI 글은 실행 계획과 설계 문서를 리포지터리 안의 기록 시스템으로 유지하는 점을 강조한다.

현재 프로젝트 적용:
- `TODO.md`, `NEXT_SESSION_PLAN.md`, `VERSION_ROADMAP.md`, `docs/V1_5_AGENT_READY_PLAN.md` 같은 문서가 이 역할을 맡는다.
- 버전별 하네스 모드와 세션 메타데이터는 `docs/HARNESS_EVOLUTION_PLAN.md`에 고정한다.

### 2. 에이전트는 큰 설명서보다 맵을 더 잘 따른다
- OpenAI 글은 거대한 단일 지침서보다, 짧은 인덱스와 연결된 문서 구조를 선호한다.
- 따라서 하네스는 "한 파일에 모든 것"이 아니라 "작은 기준 문서들의 연결"이어야 한다.

현재 프로젝트 적용:
- `AGENTS.md`는 우선순위와 규칙을 담고
- 세부 상태는 `TODO.md`, `NEXT_SESSION_PLAN.md`
- 버전 경계는 `VERSION_ROADMAP.md`
- 브랜치별 준비 작업은 `docs/V1_5_AGENT_READY_PLAN.md`
  로 분리하는 구조가 맞다.

### 3. 전문화된 역할과 명시적 검증이 품질을 끌어올린다
- Anthropic 글은 planner / generator / evaluator 분리와 sprint contract의 가치를 보여 준다.
- OpenAI 글은 검증, 리뷰, 복구 루프가 시스템 안에 인코딩될수록 자율성이 높아진다고 본다.

현재 프로젝트 적용:
- 현재는 사람/에이전트 절차 역할(`기획자/리뷰어/작업자/검수자/유지보수자`)은 있지만, 실행 산출물은 아직 약하다.
- `V1.5`에서는 최소한 `plan -> build -> validate -> trace` 산출물을 더 명확히 남겨야 한다.

### 4. 아키텍처와 취향은 문서만으로 부족하고 기계적으로도 강제해야 한다
- OpenAI 글은 문서뿐 아니라 custom lint, structural test, invariants를 강조한다.

현재 프로젝트 적용:
- 지금의 `roadmap_harness.py`는 문서 일관성 검증만 한다.
- 앞으로는 구조 규칙도 조금씩 기계 검증으로 승격하는 것이 맞다.

### 5. 관측 가능성과 피드백 루프가 장기 실행의 핵심이다
- OpenAI 글은 로그/메트릭/트레이스 같은 관측 가능성 신호를 작업 루프 안에 넣는다.
- Anthropic 글은 evaluator가 실제 앱을 사용해 문제를 찾는 루프를 강조한다.

현재 프로젝트 적용:
- `ops-baseline`, `runtime_preflight`, `/health`, route timing 로그는 이미 좋은 출발점이다.
- 다만 이것이 "하네스 레이어"로 문서화되어 있지는 않았다.

### 6. 자율성이 높을수록 가비지 컬렉션 루프가 필요하다
- OpenAI 글은 드리프트와 패턴 복제를 막기 위한 정기 정리 루프를 강조한다.

현재 프로젝트 적용:
- 현재는 사람이 문서/코드 드리프트를 눈으로 정리하는 비중이 높다.
- 장기적으로는 하네스 드리프트 점검과 작은 정리 PR을 주기적으로 만드는 쪽이 맞다.

## Harness Layers For Trunk RAG

### Layer 1. Control Plane
- 목적: 지금 무엇을 해야 하는지 정한다.
- 현재 아티팩트:
  - `TODO.md`
  - `NEXT_SESSION_PLAN.md`
  - `AGENTS.md`
  - `WORKFLOW.md`

핵심 규칙:
- 최상위 `active`는 1개만
- `NEXT_SESSION_PLAN`은 `TODO`의 `active`와 동기화
- 브랜치 작업은 공식 `active`를 자동 대체하지 않음

### Layer 2. Product Boundary
- 목적: 현재 제품이 어디까지인지 정한다.
- 현재 아티팩트:
  - `VERSION_ROADMAP.md`
  - `docs/V1_5_AGENT_READY_PLAN.md`
  - `SPEC.md`

핵심 질문:
- 지금 작업은 `V1` 안정화인가, `V1.5` 준비인가, `V2` 기능인가
- 현재 브랜치가 공식 active loop보다 우선하는가

### Layer 3. Evaluator / Gate
- 목적: 무엇이 통과인지 정한다.
- 현재 아티팩트:
  - `scripts/roadmap_harness.py`
  - `scripts/runtime_preflight.py`
  - `scripts/check_ops_baseline_gate.py`
  - `pytest`

핵심 질문:
- 문서 일관성이 맞는가
- 런타임 준비 상태가 맞는가
- 운영 회귀 게이트가 유지되는가

### Layer 4. Observability
- 목적: 실패 원인을 찾을 수 있게 한다.
- 현재 신호:
  - `/health`
  - runtime profile
  - embedding fingerprint
  - route reason
  - budget profile
  - timing logs

핵심 질문:
- 실패가 재현 가능한가
- 실패가 어느 단계에서 발생했는가
- 다음 복구 경로가 명확한가

### Layer 5. Guardrails
- 목적: 에이전트가 위험하게 퍼지지 않게 한다.
- 현재 가드레일:
  - MVP 우선 정책
  - GraphRAG / desktop 보류
  - 문서 우선순위
  - 완료 조건
  - 브랜치 정책

### Layer 6. Garbage Collection
- 목적: 드리프트를 작은 단위로 제거한다.
- 현재 상태:
  - 수동 정리 위주
  - 일부 문서/하네스 검증만 자동

권장 방향:
- 하네스 드리프트 점검 항목을 주기적으로 실행
- 문서/검증/구조 규칙 중 반복되는 것은 스크립트로 승격

## Workbook

아래 질문은 새 하네스나 새 작업 묶음을 만들 때 그대로 복사해서 사용한다.

### A. Scope Workbook
- 이 작업은 `V1`, `V1.5`, `V2`, `V3` 중 어디에 속하는가
- 공식 `active` 루프인가, 브랜치 전용 후속 작업인가
- 기본 사용자 경로를 바꾸는가, 내부 구조만 바꾸는가
- 무엇을 절대 범위 밖으로 둘 것인가

### B. Record-System Workbook
- 이 작업의 기준 문서는 어디에 둘 것인가
- 에이전트가 다음 세션에도 같은 판단을 하려면 어떤 문서가 필요한가
- 이 문서는 인덱스 문서인가, 상세 계약 문서인가, 실행 로그 문서인가

### C. Evaluator Workbook
- 통과/실패 기준은 무엇인가
- 정적 검증은 무엇인가
- 런타임 검증은 무엇인가
- 메인 경로 회귀는 무엇인가
- 실패 시 어떤 진단 코드나 로그가 남아야 하는가

### D. Guardrail Workbook
- 이 작업이 건드리면 안 되는 경계는 무엇인가
- 어떤 경우 사용자 확인이 필요한가
- 어떤 작업은 자동 진행하고 어떤 작업은 멈춰야 하는가

### E. Drift Workbook
- 이 작업으로 생길 수 있는 드리프트는 무엇인가
- 나중에 반복해서 점검할 항목은 무엇인가
- 문서 규칙인지, 스크립트 규칙인지, 린트 규칙인지 구분했는가

## Copy-Paste Template

```md
# Harness Worksheet

## 1. Work Identity
- version_track:
- branch_scope:
- official_active_loop:
- user_visible_change:

## 2. Scope
- in:
- out:
- assumptions:

## 3. Record System
- source_of_truth_docs:
- execution_doc:
- handoff_doc_updates:

## 4. Evaluators
- static_checks:
- targeted_tests:
- regression_gate:
- runtime_signals:

## 5. Guardrails
- do_not_expand_into:
- escalation_conditions:
- rollback_or_recovery_path:

## 6. Drift / Hygiene
- likely_drift_points:
- scheduled_cleanup_rule:
- candidate_future_automation:
```

## Trunk RAG Review

### Current Strengths
- 단일 `active` 루프가 명확하다.
- `TODO.md`와 `NEXT_SESSION_PLAN.md`를 통한 기록 시스템이 이미 있다.
- `ops-baseline`, `runtime_preflight`, `/health`가 evaluator 역할을 실제로 수행한다.
- 최근 보강으로 feature 브랜치에서도 공식 `active`가 우선이라는 경고가 하네스 상태 출력에 나타난다.

### Current Weak Spots
- `roadmap_harness.py`는 아직 문서 구조 검증 중심이고, 구조 규칙/검증 커버리지까지 보지는 못한다.
- substantial task에 대한 별도 `execution contract` 문서가 항상 생기지는 않는다.
- 관측 가능성 신호가 강하지만, 이를 하네스 레이어로 묶은 문서가 이제 막 생겼다.
- 드리프트 정리 루프는 아직 사람 중심이다.

### Recommended Next Steps
1. 큰 작업에는 `Harness Worksheet`를 별도 문서로 남긴다.
2. `V1.5`의 각 WP마다 plan / build / validate / trace 산출물을 남긴다.
3. `roadmap_harness.py`의 다음 확장 후보를 정의한다.
   - 기준 문서 존재 여부 검사
   - 브랜치 계획 문서와 공식 active loop의 관계 검사
   - 검증 명령 존재 여부와 스크립트 실제 존재 여부 검사
4. 장기적으로 "하네스 가비지 컬렉션"용 작은 정리 체크를 별도 스크립트로 분리한다.

## Adoption Rules
- 새 브랜치를 만든다고 새 공식 active loop가 생기는 것은 아니다.
- 새 버전 준비 작업은 공식 `active`와 충돌하지 않는 한 브랜치 문서로만 분리한다.
- 반복해서 확인되는 규칙은 문서 설명에 머무르지 말고 하네스/테스트/린트로 승격한다.
- 에이전트가 못하는 부분은 모델 탓으로 끝내지 말고, 하네스에 무엇이 빠졌는지 먼저 본다.
