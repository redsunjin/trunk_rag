# 분야별 컬렉션 + 단순 라우팅 정책

목적:
- `trunk_rag`를 경량으로 유지하면서 데이터 확장성을 확보한다.
- 검색 범위를 줄여 속도/정확도를 안정화한다.

## 1) 기본 원칙

1. 컬렉션은 분야(도메인) 단위로 분리한다.
2. 질의 시에는 "단순 라우팅"으로 대상 컬렉션을 결정한다.
3. 라우팅 실패 시 기본 컬렉션으로 fallback 한다.

## 2) 컬렉션 구조 예시

- `rag_science_history_eu`
- `rag_science_history_fr`
- `rag_science_history_ge`
- `rag_science_history_it`
- `rag_science_history_uk`

초기에는 소수 컬렉션(2~5개)만 운영하고, 필요 시 점진적으로 확장한다.

## 3) 라우팅 방식 (Simple)

우선순위:
1. 사용자 명시 선택(가장 우선)
2. 규칙 기반 키워드 매핑
3. 기본 컬렉션 fallback

키워드 매핑 예:
- "프랑스", "france" -> `rag_science_history_fr`
- "독일", "germany" -> `rag_science_history_ge`

## 4) 다중 분야 질의 처리

기본 모드:
- 1개 컬렉션만 조회

확장 모드(옵션):
- 최대 2개 컬렉션 병렬 조회 후 상위 결과 병합
- 기본 모드는 유지하고, 필요 시에만 활성화

## 5) 운영 가이드

1. 컬렉션 수를 과도하게 늘리지 않는다.
2. 컬렉션별 용량 정책은 `docs/VECTORSTORE_POLICY.md`를 따른다.
3. 신규 컬렉션 생성 시 도메인 정의와 라우팅 규칙을 함께 등록한다.
