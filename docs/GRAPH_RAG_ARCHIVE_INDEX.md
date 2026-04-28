# GraphRAG Archive Index

## 상태
- GraphRAG 트랙은 `2026-03-20` 기준 잠정 중단 상태다.
- 현재 `trunk_rag` 본체 기본 경로에는 GraphRAG를 포함하지 않는다.
- 본체 기본 게이트는 `generic-baseline`이며, GraphRAG 문서는 참고용 아카이브로만 유지한다.

## 현재 본체 기준과의 경계
- 본체 기본 answer-level 질문셋: [QUERY_EVAL_QUESTION_SET.md](/Users/Agent/ps-workspace/trunk_rag/docs/QUERY_EVAL_QUESTION_SET.md)
- 본체 기본 회귀 게이트: `scripts/check_ops_baseline_gate.py` -> `generic-baseline`
- sample-pack 호환성 평가는 `sample-pack-baseline`으로 별도 유지
- 현재 graph-lite PoC 계약은 [GRAPH_LITE_RELATION_SIDECAR_CONTRACT.md](/Users/Agent/ps-workspace/trunk_rag/docs/GRAPH_LITE_RELATION_SIDECAR_CONTRACT.md)를 따른다. 이 계약은 full Neo4j/GraphRAG archive를 제품 기본 경로로 되살리는 것이 아니다.

## 아카이브 문서
- [GRAPH_RAG_QUESTION_SET.md](/Users/Agent/ps-workspace/trunk_rag/docs/GRAPH_RAG_QUESTION_SET.md)
- [GRAPH_RAG_SIDECAR_CONTRACT.md](/Users/Agent/ps-workspace/trunk_rag/docs/GRAPH_RAG_SIDECAR_CONTRACT.md)
- [GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md](/Users/Agent/ps-workspace/trunk_rag/docs/reports/GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md)
- [GRAPH_RAG_ACTUAL_POC_REPORT_2026-03-17.md](/Users/Agent/ps-workspace/trunk_rag/docs/reports/GRAPH_RAG_ACTUAL_POC_REPORT_2026-03-17.md)
- [QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md](/Users/Agent/ps-workspace/trunk_rag/docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md)
- [GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md](/Users/Agent/ps-workspace/trunk_rag/docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md)

## 사용 원칙
- 현재 운영/릴리즈 판단에는 이 문서군을 직접 사용하지 않는다.
- 과거 판단 근거, PoC 맥락, 재개 조건 검토가 필요할 때만 참조한다.
