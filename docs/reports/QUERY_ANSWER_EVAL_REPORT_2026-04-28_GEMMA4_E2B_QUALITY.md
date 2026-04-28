# Query Answer Eval Report

## Scope
- generated_at: `2026-04-28T03:07:00+00:00`
- backend: `vector_query`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8000`
- llm_provider: `ollama`
- llm_model: `gemma4:e2b`

## Health Snapshot
- vectors: `37`
- chunking_mode: `char`
- embedding_model: `BAAI/bge-m3`
- default_llm_provider: `ollama`
- default_llm_model: `gemma4:e4b`

## Summary
- cases: `6`
- passed: `5`
- pass_rate: `0.8333`
- avg_weighted_score: `0.7962`
- avg_latency_ms: `2370.421`
- p95_latency_ms: `3568.391`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Buckets
### sample-pack-baseline
- cases: `3`
- passed: `2`
- pass_rate: `0.6667`
- avg_weighted_score: `0.6724`
- avg_latency_ms: `2744.558`
- p95_latency_ms: `3834.592`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`
### generic-baseline
- cases: `3`
- passed: `3`
- pass_rate: `1.0`
- avg_weighted_score: `0.92`
- avg_latency_ms: `1996.283`
- p95_latency_ms: `2191.589`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Case Results
### GQ-01 (sample-pack-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `fr`
- actual_route_keys: `fr`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `4012.06`
- required_hits: `4/4`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `1`
- source_route_coverage: `1.0`
- answer_preview: `요약하면, 에콜 폴리테크니크의 역할은 프랑스 과학 인재 양성을 국가 중심의 교육과 훈련으로 조직한 데 있습니다. 에콜 폴리테크니크는 프랑스 혁명기의 혼란과 외세의 위협 속에서 국가가 직접 엘리트 과학 인재를 육성하여 사회를 혁신하는 프랑스 특유의 모델을 완성했습니다. 이 기관은 세계 최초의 이공계 전문 교육 기관으로서 수학, 물리뿐만 아니라 토목, 교량 건설, 주조 및 단조 등 전쟁과 국가 재건에 필요한 실전 기술을 교육했습니`
### GQ-03 (sample-pack-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `uk`
- actual_route_keys: `uk`
- route_pass: `True`
- weighted_score: `0.96`
- latency_ms: `2237.385`
- required_hits: `5/5`
- must_include_any_hits: `4/5`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `1`
- source_route_coverage: `1.0`
- answer_preview: `요약하면, 뉴턴의 국장은 영국 사회에서 과학자의 권위와 영향력이 국왕에 비견될 만큼 높아졌음을 상징했습니다. 이는 과학이 종교나 왕권 못지않은 사회적 지위를 얻었다는 뜻입니다. 아이작 뉴턴의 국장은 영국 역사상 전례 없는 '사회적 지진'을 일으켰으며, 평민 출신 학자가 국왕들이 잠든 웨스트민스터 사원에 안치된 사건이었습니다. 이는 과학이 종교 및 왕권과 동등한 권위를 획득했음을 선포한 사건으로, 과학이 신분과 권위의 상징인 사`
### GQ-05 (sample-pack-baseline)
- pass: `False`
- status: `200`
- request_mode: `explicit_multi`
- expected_route_keys: `fr, ge`
- actual_route_keys: `fr, ge`
- route_pass: `True`
- weighted_score: `0.1237`
- latency_ms: `1984.228`
- required_hits: `0/4`
- must_include_any_hits: `0/4`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `제공된 문서에서 확인되지 않습니다.`
### GQ-19 (generic-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.88`
- latency_ms: `2213.226`
- required_hits: `2/2`
- must_include_any_hits: `2/5`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `에콜 폴리테크니크는 국가적 위기 상황에서 과학을 최후의 보루로 삼아 국가가 직접 엘리트 과학 인재를 육성하는 방식으로 인재를 길렀습니다. 이곳에서는 수학과 물리뿐만 아니라 토목, 교량 건설, 주조 및 단조 등 전쟁과 국가 재건에 필요한 실전 기술을 교육했습니다. 이러한 실용적 교육과 과학적 표준화 작업은 근대 산업의 강력한 기반이 되었으며, 이는 훗날 전 세계 주요 공과대학의 모태가 되는 교육 유산으로 이어졌습니다.`
### GQ-20 (generic-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.96`
- latency_ms: `1996.852`
- required_hits: `4/4`
- must_include_any_hits: `4/5`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `이제 과학이 신분과 권위의 상징인 사원에 입성하여 사회적 지위의 정점에 서게 되었음을 보여줍니다. 1727년 아이작 뉴턴의 국장이 국왕들이 잠든 웨스트민스터 사원에 안치된 것은 과학이 종교 및 왕권과 동등한 권위를 획득했음을 선포한 사건이었습니다. 이로 인해 당시 영국은 신분을 넘어 지식과 능력을 국격으로 예우하는 문화를 가졌음을 선포한 것입니다.`
### GQ-21 (generic-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.92`
- latency_ms: `1778.772`
- required_hits: `3/3`
- must_include_any_hits: `3/5`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `독일은 나폴레옹 전쟁 패배 후 국가 재건의 핵심 동력을 교육과 과학에서 찾았습니다. 1810년에 설립된 베를린 대학(현 훔볼트 대학)은 연구와 교육을 통합하는 새로운 대학 모델을 제시하며 세계 과학의 요람으로 발전했습니다. 이러한 기초 과학의 제도화는 독일이 실용적 공학을 산업에 접목하는 결정적인 발판이 되었습니다.`
