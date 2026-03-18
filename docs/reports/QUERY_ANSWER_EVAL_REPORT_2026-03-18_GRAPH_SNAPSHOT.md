# Query Answer Eval Report

## Scope
- generated_at: `2026-03-18T12:52:44+00:00`
- backend: `graph_snapshot`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8000`
- llm_provider: `ollama`
- llm_model: `-`

## Health Snapshot
- vectors: `48`
- chunking_mode: `graph_snapshot`
- embedding_model: `graph_snapshot`
- default_llm_provider: `graph_snapshot`
- default_llm_model: `-`

## Graph Snapshot
- graph_nodes: `20`
- graph_edges: `48`
- graph_source_docs: `5`
- graph_section_hits: `21`
- graph_max_hops: `2`

## Summary
- cases: `3`
- passed: `2`
- pass_rate: `0.6667`
- avg_weighted_score: `0.8444`
- avg_latency_ms: `0.051`
- p95_latency_ms: `0.074`

## Buckets
### graph-candidate
- cases: `3`
- passed: `2`
- pass_rate: `0.6667`
- avg_weighted_score: `0.8444`
- avg_latency_ms: `0.051`
- p95_latency_ms: `0.074`

## Case Results
### GQ-09 (graph-candidate)
- pass: `False`
- status: `200`
- request_mode: `explicit_multi`
- expected_route_keys: `uk, ge, fr`
- actual_route_keys: `uk, ge, fr`
- route_pass: `True`
- weighted_score: `0.7333`
- latency_ms: `0.033`
- required_hits: `5/6`
- must_include_any_hits: `0/4`
- forbidden_hits: `-`
- answer_preview: `질문 재진술: 뉴턴의 국장, 볼테르의 충격, 프랑스/독일 계몽주의 확산이 어떤 연쇄로 이어졌는지 설명해줘.
그래프 스냅샷 기준 관계망 요약입니다.
핵심 엔티티: 계몽주의, 뉴턴, 볼테르
확장 엔티티: 계몽주의, 독일 물리학회, 헬름홀츠, 훔볼트 대학, 라이프니츠, 마그누스 실험실, 나폴레옹 전쟁, 뉴턴
관계 근거:
- Leibniz <-> Newton | weight=3 | eu_summry.md: 3. 조피 도로테아: 프리드`
### GQ-12 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `ge`
- actual_route_keys: `ge`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `0.042`
- required_hits: `5/5`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- answer_preview: `질문 재진술: 마그누스 실험실에서 시작된 네트워크가 헬름홀츠, 지멘스, 독일 물리학회, 산업화로 어떻게 이어졌는지 설명해줘.
그래프 스냅샷 기준 관계망 요약입니다.
핵심 엔티티: 독일 물리학회, 헬름홀츠, 마그누스 실험실, 지멘스
확장 엔티티: 계몽주의, 독일 물리학회, 헬름홀츠, 훔볼트 대학, 라이프니츠, 마그누스 실험실, 나폴레옹 전쟁, 뉴턴
관계 근거:
- Leibniz <-> Newton | weight=3 | eu_s`
### GQ-15 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.8666`
- latency_ms: `0.078`
- required_hits: `6/6`
- must_include_any_hits: `2/6`
- forbidden_hits: `-`
- answer_preview: `질문 재진술: 에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학을 한 관계망으로 놓고 각자의 역할을 설명해줘.
그래프 스냅샷 기준 관계망 요약입니다.
핵심 엔티티: 에콜 폴리테크니크, 훔볼트 대학, 파도바 대학, 왕립학회
확장 엔티티: 볼로냐, 에콜 폴리테크니크, 계몽주의, 프랑스 혁명, 갈릴레오, 독일 물리학회, 런던 대화재, 헬름홀츠
관계 근거:
- Leibniz <-> Newton | weight=3 | eu_su`
