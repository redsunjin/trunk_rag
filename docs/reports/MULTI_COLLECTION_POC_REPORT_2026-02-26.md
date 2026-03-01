# 다중 컬렉션 조회 PoC 벤치 메모 (2026-02-26)

목적:
- 단일 컬렉션 대비 다중 컬렉션(최대 2개) 조회의 지연/커버리지 영향을 빠르게 확인한다.
- 운영 기본값(single vs multi)을 결정하기 위한 1차 근거를 남긴다.

## 1) 측정 조건

- 스크립트: `scripts/benchmark_multi_collection.py`
- 실행 명령:
  - `.venv\Scripts\python.exe scripts\benchmark_multi_collection.py --reindex --rounds 5 --output docs\reports\multi_collection_benchmark_2026-02-26.json`
- 측정 대상:
  - `single_all` = `["all"]`
  - `single_fr` = `["fr"]`
  - `dual_fr_ge` = `["fr","ge"]`
- 질의 5개 x 라운드 5회 = 시나리오당 25회 측정
- 본 벤치는 "검색 단계" 중심이다. LLM 생성 시간은 제외된다.

## 2) 인덱스 상태

- `all`: vectors=37, docs=5
- `fr`: vectors=7, docs=1
- `ge`: vectors=7, docs=1

## 3) 결과 요약

| scenario | latency_avg_ms | latency_p95_ms | docs_avg | source_count_avg |
|---|---:|---:|---:|---:|
| single_all | 460.360 | 597.682 | 3.0 | 2.2 |
| single_fr | 492.741 | 633.080 | 3.0 | 1.0 |
| dual_fr_ge | 981.901 | 1156.695 | 6.0 | 2.0 |

## 4) 해석

- `dual_fr_ge`는 `single_fr` 대비:
  - p95 지연 약 `+82.7%` (633.080 -> 1156.695ms)
  - 평균 문서 수 `2배` (3.0 -> 6.0)
  - 평균 source 수 `2배` (1.0 -> 2.0)
- 즉, 다중 컬렉션은 커버리지(근거 폭) 이점이 있으나 지연 비용이 큼.

## 5) 운영 권고 (1차)

1. 기본값은 단일 컬렉션 유지 (`single`).
2. 다중 컬렉션은 "교차 국가/교차 도메인 질문"에서만 옵션으로 사용.
3. 운영 도입 시 p95 임계(예: 1.2s) 모니터링을 추가해 자동/수동 fallback 기준을 둔다.

## 6) 후속 작업

1. 실제 `/query` end-to-end(LLM 포함) p95 계측 추가
2. 다중 컬렉션 선택 시 상위 문서 수(k) 동적 조정 검토 (지연 완화 목적)
3. 요청 패턴 기반으로 다중 컬렉션 자동 추천 규칙 검증
