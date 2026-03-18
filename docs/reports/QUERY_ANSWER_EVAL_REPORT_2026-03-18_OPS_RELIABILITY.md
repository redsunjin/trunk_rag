# Query Answer Eval Report

## Scope
- generated_at: `2026-03-18T22:58:18+00:00`
- backend: `vector_query`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8000`
- llm_provider: `ollama`
- llm_model: `llama3.1:8b`

## Health Snapshot
- vectors: `37`
- chunking_mode: `char`
- embedding_model: `/Users/Agent/Documents/huggingface/models/minishlab/potion-base-4M`
- default_llm_provider: `ollama`
- default_llm_model: `qwen3:4b`

## Summary
- cases: `3`
- passed: `0`
- pass_rate: `0.0`
- avg_weighted_score: `0.8261`
- avg_latency_ms: `6733.159`
- p95_latency_ms: `9028.629`

## Buckets
### ops-baseline
- cases: `3`
- passed: `0`
- pass_rate: `0.0`
- avg_weighted_score: `0.8261`
- avg_latency_ms: `6733.159`
- p95_latency_ms: `9028.629`

## Case Results
### GQ-01 (ops-baseline)
- pass: `False`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `fr`
- actual_route_keys: `fr`
- route_pass: `True`
- weighted_score: `0.775`
- latency_ms: `6841.965`
- required_hits: `3/4`
- must_include_any_hits: `3/6`
- forbidden_hits: `-`
- answer_preview: `에콜 폴리테크니크는 프랑스 과학 인재 양성에서 국가가 직접 엘리트 과학 인재를 육성하여 사회를 혁신하는 프랑스 특유의 모델을 완성했습니다. 이는 프랑스 혁명 정부가 추진한 표준화 작업의 결과로, 근대 산업의 강력한 기반이 되었습니다. 에콜 폴리테크니크는 실용적 교육을 통해 수학, 물리, 토목, 교량 건설, 주조 및 단조 등 전쟁과 국가 재건에 필요한 실전 기술을 주입했습니다.

제공된 문서에서 확인되지 않습니다.`
### GQ-03 (ops-baseline)
- pass: `False`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `uk`
- actual_route_keys: `uk`
- route_pass: `True`
- weighted_score: `0.8784`
- latency_ms: `4085.92`
- required_hits: `5/5`
- must_include_any_hits: `2/5`
- forbidden_hits: `-`
- answer_preview: `뉴턴의 국장은 영국 사회에서 과학이 종교 및 왕권과 동등한 권위를 획득했음을 상징했습니다. 뉴턴은 평민 출신의 학자로, 국왕들이 잠든 웨스트민스터 사원에 안치된 것은 과학의 사회적 지위가 높아진 것을 나타냈습니다.`
### GQ-05 (ops-baseline)
- pass: `False`
- status: `200`
- request_mode: `explicit_multi`
- expected_route_keys: `fr, ge`
- actual_route_keys: `fr, ge`
- route_pass: `True`
- weighted_score: `0.825`
- latency_ms: `9271.592`
- required_hits: `3/4`
- must_include_any_hits: `3/4`
- forbidden_hits: `-`
- answer_preview: `프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학은 인재 양성에서 다음과 같은 차이점이 있습니다.

에콜 폴리테크니크는 프랑스 혁명기의 혼란과 외세의 위협 속에서 설립된 세계 최초의 이공계 전문 교육 기관입니다. 이곳은 단순한 학교가 아니라 국가 총동원 체제를 뒷받침하는 기술 병기창이었습니다. 실용적 교육을 통해 수학, 물리뿐만 아니라 전쟁과 국가 재건에 필요한 실전 기술을 주입했습니다. 또한, 미터법 도입 등 혁명 정부가 추진`
