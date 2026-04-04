# Generic RAG Refocus Review (2026-04-04)

## 목적
- 현재 `trunk_rag`가 "범용 RAG 제품"이 아니라 "유럽 과학사 샘플셋에 강하게 결합된 로컬 RAG" 상태라는 점을 명시한다.
- `LOOP-001` 이후 다음 분기 작업으로 무엇을 제거하고 무엇을 유지할지 고정한다.
- 새로운 기술 후보를 "지금 바로 붙일 것"과 "범용화 이후 검토할 것"으로 분리한다.

## 현재 판단
- 현재 웹 MVP 기본 경로와 운영 게이트는 유지 가치가 있다.
- 그러나 질의/컬렉션/평가/문서 구조가 특정 유럽사 샘플셋에 과도하게 맞춰져 있어, 이 상태로는 범용 RAG 제품으로 보기 어렵다.
- 따라서 다음 분기 작업의 핵심은 "성능 추가 개선"보다 "도메인 결합 제거 + 범용 평가 기준 정립"이다.

## 확인된 도메인 결합
### 1. 컬렉션 구조 하드코딩
- [core/settings.py](/Users/Agent/ps-workspace/trunk_rag/core/settings.py)
- `all/eu/fr/ge/it/uk` 컬렉션이 코드에 고정돼 있다.
- 키워드 라우팅도 국가명/언어명 기반으로 묶여 있어 범용 문서셋에는 맞지 않는다.
- `build_index.py --reset`과 운영 문서도 같은 묶음을 전제로 한다.

### 2. 질의 후처리의 질문셋 오버피팅
- [services/query_service.py](/Users/Agent/ps-workspace/trunk_rag/services/query_service.py)
- `역할/비교/상징` 전용 보정과 특정 질문형 대응이 들어가 있다.
- 이는 범용 RAG 관점에서는 retrieval/answer quality를 올리는 것이 아니라, 특정 평가셋에 맞춘 규칙 기반 보정에 가깝다.

### 3. 평가 게이트의 도메인 편향
- [evals/answer_level_eval_fixtures.jsonl](/Users/Agent/ps-workspace/trunk_rag/evals/answer_level_eval_fixtures.jsonl)
- 현재 `ops-baseline`은 사실상 유럽 과학사 3문항을 통과하는지 보는 구조다.
- 이 상태로는 "운영 가능한 범용 RAG"를 검증했다고 보기 어렵다.

### 4. 메타데이터 모델의 협소함
- `country`, `doc_type`, `collection_key`가 현재 데이터셋 구조에 맞춰져 있다.
- 범용 RAG에서는 `dataset`, `namespace`, `tags`, `visibility`, `source_type` 같은 더 중립적인 기준이 필요하다.

### 5. 문서/로드맵의 아카이브 혼재
- `README.md`, `SPEC.md`, `NEXT_SESSION_PLAN.md`, `TODO.md` 전반에 GraphRAG 아카이브와 유럽사 샘플셋 이력이 깊게 남아 있다.
- 보존은 필요하지만, 본체 제품 문서와 샘플/이력 문서를 분리하는 편이 맞다.

## 유지할 것
- 웹 MVP 기본 경로: `run_doc_rag.bat -> /intro -> /app`
- `/query` 표준 에러 계약, request id, trace/meta 노출
- runtime profile, embedding fingerprint, ops-baseline 게이트 구조
- 업로드 요청/관리자 승인 워크플로우
- managed markdown 원본 + active 버전 운영 방식
- Ollama 직접 진단 스크립트와 runtime preflight

## 줄이거나 제거할 것
### 즉시 제거/완화 후보
- 유럽사 전용 컬렉션 라벨/기본 라우팅을 본체 정책으로 유지하는 것
- 질의 후처리의 `역할/비교/상징` 규칙 기반 보정
- 운영 게이트를 유럽사 전용 질문셋만으로 대표시키는 것

### 샘플팩으로 격하할 것
- `eu/fr/ge/it/uk` 데이터셋 자체
- 유럽사 질문셋과 GraphRAG 관련 문서군
- 역사/국가 기반 컬렉션 정책

## 범용 RAG 전환의 목표 상태
- 본체는 `dataset-agnostic local RAG runtime`
- 샘플 데이터셋은 선택형 `domain pack`
- 컬렉션은 국가명이 아니라 `namespace` 또는 `dataset manifest` 기반
- 평가 하네스는 `generic baseline`과 `sample-pack baseline`을 분리

## 다음 분기에서 필요한 구조 변경
### A. 데이터/컬렉션 계층
1. `COLLECTION_CONFIGS` 하드코딩 제거
2. `dataset manifest` 또는 `collections.json` 기반 동적 로딩
3. `country/doc_type` 중심 기본값을 `dataset/tags/source_type` 중심으로 완화

### B. 질의 계층
1. 질문 유형별 규칙 후처리 제거 또는 feature flag 뒤로 이동
2. 답변 보정은 도메인 독립 규칙만 유지
3. 범용 메타데이터 필터(`dataset`, `tags`, `doc_key`) 우선

### C. 평가 계층
1. `ops-baseline`을 범용 질문셋으로 재구성
2. 유럽사 질문셋은 `sample-pack-eval`로 별도 분리
3. 모델 비교도 범용 질문셋 기준으로 다시 측정

### D. 문서 계층
1. README/SPEC는 본체 제품 기준만 남긴다
2. 샘플 데이터셋 설명은 별도 문서로 이동
3. GraphRAG/유럽사 이력은 아카이브 섹션이나 `docs/archive/`로 더 분리

## 기술적으로 가져와볼 만한 것
### 지금 바로 붙이기보다 범용화 이후 검토할 것
- Contextual Retrieval
  - chunk에 주변 문맥을 붙여 retrieval quality를 높이는 접근
  - 참고: https://www.anthropic.com/research/contextual-retrieval
- Hybrid Search
  - dense + lexical 결합으로 고유명사/정확한 용어 검색 보강
  - 참고: https://docs.pinecone.io/guides/search/search-overview
- Rerank
  - 2-stage retrieval로 top-k 결과 정밀도 개선
  - 참고: https://docs.pinecone.io/guides/search/rerank-results

## 우선순위 제안
1. `LOOP-001` 종료
2. `Generic RAG Refocus`
   - 컬렉션 하드코딩 해체
   - 유럽사 전용 후처리 제거
   - 범용 평가셋 도입
3. `Quality Upgrade`
   - hybrid search 후보
   - rerank 후보
   - contextual retrieval 후보

## 결론
- 현재 시스템은 실패한 것이 아니라 "유럽 과학사 샘플 기반 RAG MVP"로는 충분히 정리된 상태다.
- 다만 범용 RAG 제품으로 가려면 지금부터는 모델 미세 비교보다 도메인 결합 제거가 우선이다.
- 다음 분기 작업은 성능 튜닝이 아니라 `generic refocus`여야 한다.
