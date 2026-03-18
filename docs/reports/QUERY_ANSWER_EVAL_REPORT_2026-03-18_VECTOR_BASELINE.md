# Query Answer Eval Report

## Scope
- generated_at: `2026-03-18T11:57:54+00:00`
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
- cases: `6`
- passed: `2`
- pass_rate: `0.3333`
- avg_weighted_score: `0.593`
- avg_latency_ms: `8001.708`
- p95_latency_ms: `14277.843`

## Buckets
### ops-baseline
- cases: `3`
- passed: `1`
- pass_rate: `0.3333`
- avg_weighted_score: `0.3667`
- avg_latency_ms: `6252.65`
- p95_latency_ms: `13886.952`
### graph-candidate
- cases: `3`
- passed: `1`
- pass_rate: `0.3333`
- avg_weighted_score: `0.8194`
- avg_latency_ms: `9750.767`
- p95_latency_ms: `11881.034`

## Case Results
### GQ-01 (ops-baseline)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `fr`
- actual_route_keys: `fr`
- route_pass: `True`
- weighted_score: `0.9`
- latency_ms: `3729.698`
- required_hits: `4/4`
- must_include_any_hits: `3/6`
- forbidden_hits: `-`
- answer_preview: `에콜 폴리테크니크는 프랑스 과학 인재 양성에서 핵심 역할을 맡았습니다. 이곳은 세계 최초의 이공계 전문 교육 기관으로, 단순한 학교가 아니라 국가 총동원 체제를 뒷받침하는 기술 병기창이었습니다. 에콜 폴리테크니크는 실용적 교육을 제공하여 수학, 물리, 토목, 교량 건설, 주조 및 단조 등 전쟁과 국가 재건에 필요한 실전 기술을 주입했습니다. 또한 과학적 표준화를 통해 근대 산업의 강력한 기반이 되었습니다.

제공된 문서에서 확`
### GQ-03 (ops-baseline)
- pass: `False`
- status: `400`
- request_mode: `explicit_single`
- expected_route_keys: `uk`
- actual_route_keys: `-`
- route_pass: `False`
- weighted_score: `0.1`
- latency_ms: `12.716`
- required_hits: `0/5`
- must_include_any_hits: `0/5`
- forbidden_hits: `-`
- answer_preview: ``
- error: `VECTORSTORE_EMPTY` / `선택된 컬렉션에 인덱스가 없습니다. 먼저 /reindex를 실행하세요.`
### GQ-05 (ops-baseline)
- pass: `False`
- status: `504`
- request_mode: `explicit_multi`
- expected_route_keys: `fr, ge`
- actual_route_keys: `-`
- route_pass: `False`
- weighted_score: `0.1`
- latency_ms: `15015.536`
- required_hits: `0/4`
- must_include_any_hits: `0/4`
- forbidden_hits: `-`
- answer_preview: ``
- error: `LLM_TIMEOUT` / `LLM 응답 시간이 제한(15초)을 초과했습니다.`
### GQ-09 (graph-candidate)
- pass: `False`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.7333`
- latency_ms: `12064.762`
- required_hits: `5/6`
- must_include_any_hits: `0/4`
- forbidden_hits: `-`
- answer_preview: `1) 핵심 답변:
뉴턴의 국장, 볼테르의 충격, 프랑스/독일 계몽주의 확산은 다음과 같은 연쇄로 이어졌습니다.

* 뉴턴의 국장은 프랑스의 과학적 발전을 촉진했습니다.
* 볼테르의 충격은 프랑스의 계몽주의를 확산시켰습니다.
* 프랑스/독일 계몽주의 확산은 근대 이성의 설계자로 프랑스를 만들었습니다.

2) 근거:
* 뉴턴의 국장은 프랑스의 과학적 발전을 촉진했다는 점에서, "루이 14세는 과학을 국가 권력을 홍보하는 강력한 '`
### GQ-12 (graph-candidate)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `ge`
- actual_route_keys: `ge`
- route_pass: `True`
- weighted_score: `0.9334`
- latency_ms: `6960.053`
- required_hits: `5/5`
- must_include_any_hits: `4/6`
- forbidden_hits: `-`
- answer_preview: `1) 핵심 답변:
마그누스 실험실에서 시작된 네트워크는 헬름홀츠, 지멘스, 독일 물리학회, 산업화로 이어졌습니다. 구스타프 마그누스의 사설 실험실은 신분과 배경을 초월한 지적 교류의 장이었습니다. 이곳에서 군 장교 출신의 지멘스와 가난한 의대생 헬름홀츠가 만났으며, 이 네트워크는 세계 최초의 물리학회인 독일 물리학회(DPG)의 모태가 되었습니다. 이러한 기초 과학의 제도화는 독일이 실용적 공학을 산업에 접목하는 결정적 발판이 `
### GQ-15 (graph-candidate)
- pass: `False`
- status: `200`
- request_mode: `fallback_all_for_eval`
- expected_route_keys: `all`
- actual_route_keys: `all`
- route_pass: `True`
- weighted_score: `0.7916`
- latency_ms: `10227.485`
- required_hits: `5/6`
- must_include_any_hits: `2/6`
- forbidden_hits: `-`
- answer_preview: `에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학은 모두 과학 교육과 연구를 위한 기관입니다.

에콜 폴리테크니크는 프랑스 혁명기에 설립되어 과학 군인을 양성하는 목적으로 설립된 기관입니다. 몽주, 카르노, 라부아지에 등은 이 기관을 통해 과학적 방패가 되었습니다.

훔볼트 대학은 1810년 설립된 베를린 대학의 이름을 따온 기관으로, 연구와 교육의 통합이라는 새로운 대학 모델을 제시하며 아인슈타인과 막스 플랑크를 배출`
