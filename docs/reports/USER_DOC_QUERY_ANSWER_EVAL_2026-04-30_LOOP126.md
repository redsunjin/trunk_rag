# Query Answer Eval Report

## Scope
- generated_at: `2026-04-29T22:10:40+00:00`
- backend: `vector_query`
- eval_file: `evals/user_doc_answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8015`
- llm_provider: `ollama`
- llm_model: `gemma4:e4b`
- query_timeout_seconds: `60`
- quality_mode: `-`
- quality_stage: `-`

## Health Snapshot
- vectors: `37`
- chunking_mode: `char`
- embedding_model: `BAAI/bge-m3`
- default_llm_provider: `ollama`
- default_llm_model: `gemma4:e4b`

## Summary
- cases: `1`
- passed: `1`
- pass_rate: `1.0`
- avg_weighted_score: `1.0`
- avg_latency_ms: `12349.821`
- p95_latency_ms: `12349.821`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Buckets
### user-doc-candidate
- cases: `1`
- passed: `1`
- pass_rate: `1.0`
- avg_weighted_score: `1.0`
- avg_latency_ms: `12349.821`
- p95_latency_ms: `12349.821`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- avg_source_route_coverage: `1.0`

## Case Results
### UDQ-BC-01 (user-doc-candidate)
- pass: `True`
- status: `200`
- request_mode: `explicit_single`
- expected_route_keys: `project_docs`
- actual_route_keys: `project_docs`
- route_pass: `True`
- weighted_score: `1.0`
- latency_ms: `12349.821`
- required_hits: `4/4`
- must_include_any_hits: `5/5`
- forbidden_hits: `-`
- support: `supported` / `multiple_context_segments`
- citations: `2`
- source_route_coverage: `1.0`
- graph_lite: status=`disabled`, header=`disabled`, relations=`0`, context_added=`False`, fallback=`-`
- answer_preview: `문서 근거로 확인되는 내용입니다.
- 'graph-lite=not-reported': Server response did not include graph-lite metadata. 운영자는 다음을 확인합니다: Confirm server was started with current code and debug metadata.
- graph-lite=hit | relations=<number> | context=added
- 'g`
