# Ops Baseline Gate Report

- generated_at: `2026-05-21T12:25:38+00:00`
- ready: `True`
- base_url: `http://127.0.0.1:8000`
- llm_provider: `ollama`
- llm_model: `gemma4:e4b`

## Runtime Preflight
- ready: `True`
- app_health: ready=`True` message=`ready`
- embedding_model: ready=`True` message=`local model cache/path detected: /Users/Agent/.cache/huggingface/hub/models--BAAI--bge-m3`
- runtime_profile: ready=`True` message=`현재 Ollama 런타임 프로파일은 gemma4 기본 로컬 운영 경로로 검증됐습니다.`
- ollama: ready=`True` message=`ready`

## Core Runtime Collections
- all: vectors=`37`, ready=`True`

## Eval Target
- selected_buckets: `generic-baseline`

## Ops Baseline Eval
- cases: `3`
- passed: `3`
- pass_rate: `1.0`
- avg_weighted_score: `0.96`
- avg_latency_ms: `4654.139`
- p95_latency_ms: `4843.711`
