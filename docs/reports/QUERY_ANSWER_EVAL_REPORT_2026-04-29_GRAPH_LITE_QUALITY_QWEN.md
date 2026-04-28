# Query Answer Eval Report

## Scope
- generated_at: `2026-04-28T16:22:00+00:00`
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
- passed: `3`
- pass_rate: `1.0`
- avg_weighted_score: `0.9167`
- avg_latency_ms: `9601.656`
- p95_latency_ms: `12973.058`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Buckets
### graph-candidate
- cases: `3`
- passed: `3`
- pass_rate: `1.0`
- avg_weighted_score: `0.9167`
- avg_latency_ms: `9601.656`
- p95_latency_ms: `12973.058`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Case Results
### GQ-09 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.85`
- latency_ms: `13522.057`
- required_hits: `6/6`
- must_include_any_hits: `1/4`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `1727 년 뉴턴의 웨스트민스터 사원 국장은 평민 출신 과학자가 왕과 동등한 권위를 가진 사건으로, 볼테르가 이를 목격하며 영국의 개방성과 지성의 힘을 발견했습니다. 이 충격은 프랑스와 독일의 지식인들에게 전파되어 신분제의 벽을 넘어선 계몽주의 확산의 결정적 계기가 되었습니다. 반면 라이프니츠는 정치적 이해관계로 인해 하노버 왕가의 즉위 이후 외면당하며 잊혀졌고, 이는 과학이 국가 간 대결과 권력 구조에 따라 좌우되는 연쇄를 `
### GQ-12 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `ge`
- actual_route_keys: `ge`
- route_pass: `True`
- weighted_score: `0.9666`
- latency_ms: `7250.847`
- required_hits: `5/5`
- must_include_any_hits: `5/6`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `1`
- source_route_coverage: `1.0`
- answer_preview: `마그누스 실험실은 신분과 배경을 초월한 지적 교류의 장으로 기능하며, 군 장교 출신인 지멘스와 가난한 의대생 헬름홀츠가 만나는 네트워크의 중심이 되었습니다. 이 두 인물이 맺은 연결고리는 이후 세계 최초의 물리학회인 독일 물리학회의 모태로 발전하여 기초 과학의 제도화를 이루었습니다. 이렇게 형성된 학문적 네트워크는 실용적 공학으로 이어져 산업화에 접목되었고, 결국 독일의 국가 재건과 기술 문화 융합이라는 거대한 흐름을 만들어냈`
### GQ-15 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `8032.065`
- required_hits: `6/6`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- answer_preview: `제공된 문서에는 에콜 폴리테크니크와 훔볼트 대학의 상세한 역할은 기술되어 있으나, 왕립학회와 파도바 대학이 에콜 폴리테크니크 및 훔볼트 대학과 직접적인 관계망으로 연결되거나 상호작용하는 내용은 포함되어 있지 않습니다. 따라서 네 기관을 하나의 통합된 관계망으로 설명하거나 각자의 역할을 비교하여 서술할 수 있는 근거가 부족합니다. 문서에 따르면 에콜 폴리테크니크는 프랑스 혁명과 전쟁이라는 국가적 위기 속에서 실용적 기술 인재를 `
