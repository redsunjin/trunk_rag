# Query Answer Eval Report

## Scope
- generated_at: `2026-04-28T16:04:09+00:00`
- backend: `vector_query`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8011`
- llm_provider: `ollama`
- llm_model: `qwen3.5:9b-nvfp4`
- query_timeout_seconds: `120`
- quality_mode: `quality`
- quality_stage: `quality`

## Health Snapshot
- vectors: `37`
- chunking_mode: `char`
- embedding_model: `BAAI/bge-m3`
- default_llm_provider: `ollama`
- default_llm_model: `gemma4:e4b`

## Summary
- cases: `3`
- passed: `2`
- pass_rate: `0.6667`
- avg_weighted_score: `0.8667`
- avg_latency_ms: `12364.033`
- p95_latency_ms: `15272.702`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Buckets
### graph-candidate
- cases: `3`
- passed: `2`
- pass_rate: `0.6667`
- avg_weighted_score: `0.8667`
- avg_latency_ms: `12364.033`
- p95_latency_ms: `15272.702`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Case Results
### GQ-09 (graph-candidate)
- pass: `False`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.7333`
- latency_ms: `13668.702`
- required_hits: `5/6`
- must_include_any_hits: `0/4`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `1727년 뉴턴의 웨스트민스터 사원 국장은 평민 출신 과학자가 왕과 동등한 권위를 가짐을 보여준 충격적인 사건으로, 이를 목격한 프랑스의 볼테르는 영국의 개방성과 지성계 계몽주의 확산의 결정적 계기를 얻었습니다. 반면 독일에서는 하노버 왕조가 뉴턴 지지자를 회유하기 위해 라이프니츠를 외면함으로써 그의 종말이 비극적으로 이루어졌고, 이는 정치적 이해관계와 과학이 결합된 유럽 지적 네트워크의 격변을 보여주었습니다. 볼테르의 영국 `
### GQ-12 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `ge`
- actual_route_keys: `ge`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `15450.924`
- required_hits: `5/5`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `1`
- source_route_coverage: `1.0`
- answer_preview: `구스타프 마그누스의 사설 실험실은 신분과 배경을 초월한 지적 교류의 장으로 기능하며, 가난한 의대생 헬름홀츠와 군 장교 출신 지멘스가 만나는 네트워크를 형성했습니다. 이 두 인물의 만남과 협력은 세계 최초의 물리학회인 독일 물리학회의 모태가 되어 기초 과학 연구 체계를 제도화하는 결정적 계기가 되었습니다. 이렇게 정립된 기초 과학의 성과는 기업가 정신과 결합되어 실용적 공학으로 발전했고, 이를 통해 독일은 나폴레옹 전쟁 이후 `
### GQ-15 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `7972.474`
- required_hits: `6/6`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `제공된 문서에는 에콜 폴리테크니크와 훔볼트 대학의 역할은 기술 병기창과 연구 교육 통합 모델로 명확히 기술되어 있으나, 왕립학회와 파도바 대학에 대한 구체적인 정보는 포함되어 있지 않습니다. 따라서 네 기관을 하나의 관계망으로 연결하여 각자의 역할을 설명하는 것은 문서 근거가 부족합니다. 에콜 폴리테크니크는 프랑스 혁명과 전쟁이라는 국가적 위기 속에서 실용적 이공계 인재를 양성한 세계 최초의 전문 교육 기관으로서, 훔볼트 대학`
