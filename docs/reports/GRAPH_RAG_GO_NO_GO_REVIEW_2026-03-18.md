# GraphRAG Go/No-Go Review (2026-03-18)

## 입력 기준
- Vector baseline: `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`
- Graph snapshot compare: `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md`
- Sidecar contract: `docs/GRAPH_RAG_SIDECAR_CONTRACT.md`

## 관측 요약
- 현재 Vector baseline 전체 결과는 `2/6 pass`, `avg_weighted_score=0.593`, `p95_latency_ms=14277.843`였다.
- 같은 baseline에서 `GQ-03`은 `uk` 컬렉션 벡터가 `0`이라 `VECTORSTORE_EMPTY`로 실패했다.
- 같은 baseline에서 `GQ-05`는 `fr,ge` 명시 다중 컬렉션 비교 질문에서 `LLM_TIMEOUT`으로 실패했다.
- Graph snapshot backend를 `graph-candidate` 3개 케이스에만 적용한 answer-level 비교 결과는 `2/3 pass`, `avg_weighted_score=0.8444`, `p95_latency_ms=0.074`였다.
- 같은 `graph-candidate` 버킷에서 기존 Vector baseline은 `1/3 pass`, `avg_weighted_score=0.8194`였다.

## 판단
- 결론: `MVP 통합 No-Go`
- 보조 결론: `연구용 sidecar 트랙은 유지 가능`

## 이유
1. graph-candidate 버킷에서는 answer-level 개선 신호가 있었다.
2. 하지만 실제 `/query-advanced` 런타임 경로와 sidecar 장애 시 fallback 보장은 아직 구현/검증되지 않았다.
3. self-managed Neo4j 또는 동등 그래프 런타임을 운영 경로에 추가할 때의 복잡도도 아직 실측되지 않았다.
4. 현재 MVP 기본 경로에서 더 시급한 문제는 GraphRAG 통합보다 Vector baseline 신뢰성(`uk` 인덱스 부재, `fr,ge` timeout) 복구다.

## 재착수 조건
1. 명시적 sidecar 엔드포인트 또는 동등한 `/query-advanced` stub을 구현한다.
2. sidecar 실패 시 Vector fallback이 유지되는 통합 테스트를 추가한다.
3. 그래프 런타임 설치/운영 전략을 문서로 고정한다.
4. 같은 fixture로 answer-level 비교를 다시 실행해 개선이 재현되는지 확인한다.
