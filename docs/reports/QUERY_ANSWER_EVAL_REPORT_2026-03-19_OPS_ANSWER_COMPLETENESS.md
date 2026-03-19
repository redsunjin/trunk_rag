# Query Answer Eval Report

## Scope
- generated_at: `2026-03-19T11:24:08+00:00`
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
- passed: `3`
- pass_rate: `1.0`
- avg_weighted_score: `0.9645`
- avg_latency_ms: `6095.881`
- p95_latency_ms: `8724.427`

## Buckets
### ops-baseline
- cases: `3`
- passed: `3`
- pass_rate: `1.0`
- avg_weighted_score: `0.9645`
- avg_latency_ms: `6095.881`
- p95_latency_ms: `8724.427`

## Case Results
### GQ-01 (ops-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `fr`
- actual_route_keys: `fr`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `5170.764`
- required_hits: `4/4`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- answer_preview: `요약하면, 에콜 폴리테크니크의 역할은 프랑스 과학 인재 양성을 국가 중심의 교육과 훈련으로 조직한 데 있습니다. 에콜 폴리테크니크는 프랑스 과학 인재 양성에서 국가가 직접 엘리트 과학 인재를 육성하여 사회를 혁신하는 프랑스 특유의 모델을 완성했습니다. 이는 프랑스 혁명 정부가 추진한 표준화 작업의 결과로, 근대 산업의 강력한 기반이 되었습니다. 에콜 폴리테크니크는 실용적 교육을 통해 수학, 물리, 토목, 교량 건설, 주조 및 `
### GQ-03 (ops-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `uk`
- actual_route_keys: `uk`
- route_pass: `True`
- weighted_score: `0.96`
- latency_ms: `3997.601`
- required_hits: `5/5`
- must_include_any_hits: `4/5`
- forbidden_hits: `-`
- answer_preview: `요약하면, 뉴턴의 국장은 영국 사회에서 과학자의 권위와 영향력이 국왕에 비견될 만큼 높아졌음을 상징했습니다. 이는 과학이 종교나 왕권 못지않은 사회적 지위를 얻었다는 뜻입니다. 뉴턴의 국장은 영국 사회에서 과학이 종교 및 왕권과 동등한 권위를 획득했음을 상징했습니다. 뉴턴은 평민 출신의 학자로, 국왕들이 잠든 웨스트민스터 사원에 안치된 것은 과학의 사회적 지위가 높아진 것을 나타냈습니다.`
### GQ-05 (ops-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_multi`
- expected_route_keys: `fr, ge`
- actual_route_keys: `fr, ge`
- route_pass: `True`
- weighted_score: `1.0`
- latency_ms: `9119.278`
- required_hits: `4/4`
- must_include_any_hits: `4/4`
- forbidden_hits: `-`
- answer_preview: `비교하면, 프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학는 인재 양성의 목표와 방식에서 차이가 있습니다. 프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학은 인재 양성에서 다음과 같은 차이점이 있습니다.

에콜 폴리테크니크는 프랑스 혁명기의 혼란과 외세의 위협 속에서 설립된 세계 최초의 이공계 전문 교육 기관입니다. 이곳은 단순한 학교가 아니라 국가 총동원 체제를 뒷받침하는 기술 병기창이었습니다. 실용적 교육을 통해 수학, 물`
