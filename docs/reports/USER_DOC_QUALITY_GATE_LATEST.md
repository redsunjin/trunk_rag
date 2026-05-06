# User-Doc Quality Gate Report

- generated_at: `2026-05-06T13:57:54+00:00`
- ready: `True`
- base_url: `http://127.0.0.1:8000`
- llm_provider: `ollama`
- llm_model: `gemma4:e4b`

## Gate Boundary
- default_release_gate: `generic-baseline`
- default_release_gate_command: `scripts/check_ops_baseline_gate.py`
- user_doc_gate: `user-doc-candidate`
- user_doc_eval_file: `evals/user_doc_answer_level_eval_fixtures.jsonl`
- required_collection_keys: `project_docs`
- default_runtime_collection_changed: `False`

## Runtime Preflight
- ready: `True`
- app_health: ready=`True` message=`ready`
- embedding_model: ready=`True` message=`local model cache/path detected: /Users/Agent/.cache/huggingface/hub/models--BAAI--bge-m3`
- runtime_profile: ready=`True` message=`현재 Ollama 런타임 프로파일은 gemma4 기본 로컬 운영 경로로 검증됐습니다.`
- ollama: ready=`True` message=`ready`

## User-Doc Collections
- project_docs: vectors=`10`, ready=`True`

## Eval Target
- selected_buckets: `user-doc-candidate`
- selected_case_ids: `UDQ-BC-01`

## User-Doc Eval
- cases: `1`
- passed: `1`
- pass_rate: `1.0`
- avg_weighted_score: `1.0`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- p95_latency_ms: `16783.456`
