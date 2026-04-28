# RAG Quality Model Comparison

## Scope
- generated_at: `2026-04-28T03:12:06+00:00`
- outcome: `blocked`
- recommendation: `ollama:gemma4:e2b` is the strongest measured candidate, but no model satisfies the selected RAG quality gate.
- selected_candidate: `ollama:gemma4:e2b`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8000`
- selected_buckets: `generic-baseline, sample-pack-baseline`
- required_buckets: `generic-baseline, sample-pack-baseline`
- min_pass_rate: `1.0`
- min_avg_weighted_score: `0.85`
- max_p95_ms: `20000.0`

## Model Summary

| model | gate | cases | passed | pass_rate | score | support | p95_ms | failed_cases |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ollama:gemma4:e2b` | blocked | 6 | 5 | 0.8333 | 0.7962 | 1.0 | 16335.234 | 1 |

## Bucket Summary

### ollama:gemma4:e2b
- sample-pack-baseline: pass_rate=`0.6667`, score=`0.6724`, support=`1.0`, p95_ms=`2459.78`
- generic-baseline: pass_rate=`1.0`, score=`0.92`, support=`1.0`, p95_ms=`16706.249`

## Gate Checks

### ollama:gemma4:e2b
- overall_pass_rate: `fail` actual=`0.8333` expected=`>= 1.0`
- overall_avg_weighted_score: `fail` actual=`0.7962` expected=`>= 0.85`
- overall_p95_latency_ms: `pass` actual=`16335.234` expected=`<= 20000.0`
- overall_support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.avg_weighted_score: `pass` actual=`0.92` expected=`>= 0.85`
- generic-baseline.p95_latency_ms: `pass` actual=`16706.249` expected=`<= 20000.0`
- generic-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- sample-pack-baseline.pass_rate: `fail` actual=`0.6667` expected=`>= 1.0`
- sample-pack-baseline.avg_weighted_score: `fail` actual=`0.6724` expected=`>= 0.85`
- sample-pack-baseline.p95_latency_ms: `pass` actual=`2459.78` expected=`<= 20000.0`
- sample-pack-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`

## Failed Or Weak Cases

### ollama:gemma4:e2b
- GQ-05 (sample-pack-baseline): pass=`False`, score=`0.1237`, latency_ms=`2001.884`
  required_hits=`0/4`, any_hits=`0/4`, support=`supported`, citations=`2`, source_coverage=`1.0`
  answer_preview=`제공된 문서에서 확인되지 않습니다.`
