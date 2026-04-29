# RAG Quality Model Comparison

## Scope
- generated_at: `2026-04-29T05:03:02+00:00`
- outcome: `ready`
- recommendation: `ollama:qwen3.5:9b-nvfp4` satisfies the selected RAG quality gate.
- selected_candidate: `ollama:qwen3.5:9b-nvfp4`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8012`
- http_timeout_seconds: `180`
- query_timeout_seconds: `120`
- quality_mode: `quality`
- quality_stage: `quality`
- selected_buckets: `graph-candidate`
- required_buckets: `graph-candidate`
- min_pass_rate: `1.0`
- min_avg_weighted_score: `0.85`
- max_p95_ms: `20000.0`

## Model Summary

| model | gate | cases | passed | pass_rate | score | support | p95_ms | failed_cases |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ollama:qwen3.5:9b-nvfp4` | ready | 3 | 3 | 1.0 | 0.9167 | 1.0 | 4468.718 | 0 |

## Bucket Summary

### ollama:qwen3.5:9b-nvfp4
- graph-candidate: pass_rate=`1.0`, score=`0.9167`, support=`1.0`, p95_ms=`4468.718`

## Gate Checks

### ollama:qwen3.5:9b-nvfp4
- overall_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- overall_avg_weighted_score: `pass` actual=`0.9167` expected=`>= 0.85`
- overall_p95_latency_ms: `pass` actual=`4468.718` expected=`<= 20000.0`
- overall_support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- graph-candidate.pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- graph-candidate.avg_weighted_score: `pass` actual=`0.9167` expected=`>= 0.85`
- graph-candidate.p95_latency_ms: `pass` actual=`4468.718` expected=`<= 20000.0`
- graph-candidate.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`

## Failed Or Weak Cases

### ollama:qwen3.5:9b-nvfp4
- none
