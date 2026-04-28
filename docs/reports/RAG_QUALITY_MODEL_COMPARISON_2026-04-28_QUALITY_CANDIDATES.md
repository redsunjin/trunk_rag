# RAG Quality Model Comparison

## Scope
- generated_at: `2026-04-28T13:05:23+00:00`
- outcome: `blocked`
- recommendation: `ollama:qwen3.5:9b-nvfp4` is the strongest measured candidate, but no model satisfies the selected RAG quality gate.
- selected_candidate: `ollama:qwen3.5:9b-nvfp4`
- eval_file: `evals/answer_level_eval_fixtures.jsonl`
- base_url: `http://127.0.0.1:8010`
- http_timeout_seconds: `180`
- query_timeout_seconds: `120`
- quality_mode: `quality`
- quality_stage: `quality`
- selected_buckets: `generic-baseline, sample-pack-baseline`
- required_buckets: `generic-baseline, sample-pack-baseline`
- min_pass_rate: `1.0`
- min_avg_weighted_score: `0.85`
- max_p95_ms: `20000.0`

## Model Summary

| model | gate | cases | passed | pass_rate | score | support | p95_ms | failed_cases |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| `ollama:gemma4:e2b` | blocked | 6 | 5 | 0.8333 | 0.7962 | 1.0 | 4600.037 | 1 |
| `ollama:gemma4:e4b` | blocked | 6 | 4 | 0.6667 | 0.6725 | 1.0 | 7437.782 | 2 |
| `ollama:qwen3.5:9b-nvfp4` | blocked | 6 | 5 | 0.8333 | 0.9364 | 1.0 | 6729.217 | 1 |

## Bucket Summary

### ollama:gemma4:e2b
- sample-pack-baseline: pass_rate=`0.6667`, score=`0.6724`, support=`1.0`, p95_ms=`5071.167`
- generic-baseline: pass_rate=`1.0`, score=`0.92`, support=`1.0`, p95_ms=`2186.324`

### ollama:gemma4:e4b
- sample-pack-baseline: pass_rate=`0.3333`, score=`0.3851`, support=`1.0`, p95_ms=`7887.954`
- generic-baseline: pass_rate=`1.0`, score=`0.96`, support=`1.0`, p95_ms=`5063.605`

### ollama:qwen3.5:9b-nvfp4
- sample-pack-baseline: pass_rate=`0.6667`, score=`0.9395`, support=`1.0`, p95_ms=`6447.802`
- generic-baseline: pass_rate=`1.0`, score=`0.9333`, support=`1.0`, p95_ms=`6774.09`

## Gate Checks

### ollama:gemma4:e2b
- overall_pass_rate: `fail` actual=`0.8333` expected=`>= 1.0`
- overall_avg_weighted_score: `fail` actual=`0.7962` expected=`>= 0.85`
- overall_p95_latency_ms: `pass` actual=`4600.037` expected=`<= 20000.0`
- overall_support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.avg_weighted_score: `pass` actual=`0.92` expected=`>= 0.85`
- generic-baseline.p95_latency_ms: `pass` actual=`2186.324` expected=`<= 20000.0`
- generic-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- sample-pack-baseline.pass_rate: `fail` actual=`0.6667` expected=`>= 1.0`
- sample-pack-baseline.avg_weighted_score: `fail` actual=`0.6724` expected=`>= 0.85`
- sample-pack-baseline.p95_latency_ms: `pass` actual=`5071.167` expected=`<= 20000.0`
- sample-pack-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`

### ollama:gemma4:e4b
- overall_pass_rate: `fail` actual=`0.6667` expected=`>= 1.0`
- overall_avg_weighted_score: `fail` actual=`0.6725` expected=`>= 0.85`
- overall_p95_latency_ms: `pass` actual=`7437.782` expected=`<= 20000.0`
- overall_support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.avg_weighted_score: `pass` actual=`0.96` expected=`>= 0.85`
- generic-baseline.p95_latency_ms: `pass` actual=`5063.605` expected=`<= 20000.0`
- generic-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- sample-pack-baseline.pass_rate: `fail` actual=`0.3333` expected=`>= 1.0`
- sample-pack-baseline.avg_weighted_score: `fail` actual=`0.3851` expected=`>= 0.85`
- sample-pack-baseline.p95_latency_ms: `pass` actual=`7887.954` expected=`<= 20000.0`
- sample-pack-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`

### ollama:qwen3.5:9b-nvfp4
- overall_pass_rate: `fail` actual=`0.8333` expected=`>= 1.0`
- overall_avg_weighted_score: `pass` actual=`0.9364` expected=`>= 0.85`
- overall_p95_latency_ms: `pass` actual=`6729.217` expected=`<= 20000.0`
- overall_support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- generic-baseline.avg_weighted_score: `pass` actual=`0.9333` expected=`>= 0.85`
- generic-baseline.p95_latency_ms: `pass` actual=`6774.09` expected=`<= 20000.0`
- generic-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`
- sample-pack-baseline.pass_rate: `fail` actual=`0.6667` expected=`>= 1.0`
- sample-pack-baseline.avg_weighted_score: `pass` actual=`0.9395` expected=`>= 0.85`
- sample-pack-baseline.p95_latency_ms: `pass` actual=`6447.802` expected=`<= 20000.0`
- sample-pack-baseline.support_pass_rate: `pass` actual=`1.0` expected=`>= 1.0`

## Failed Or Weak Cases

### ollama:gemma4:e2b
- GQ-05 (sample-pack-baseline): pass=`False`, score=`0.1237`, latency_ms=`1992.4`
  required_hits=`0/4`, any_hits=`0/4`, support=`supported`, citations=`2`, source_coverage=`1.0`
  answer_preview=`제공된 문서에서 확인되지 않습니다.`

### ollama:gemma4:e4b
- GQ-03 (sample-pack-baseline): pass=`False`, score=`0.1316`, latency_ms=`4853.897`
  required_hits=`0/5`, any_hits=`0/5`, support=`supported`, citations=`1`, source_coverage=`1.0`
  answer_preview=`제공된 문서에서 확인되지 않습니다.`
- GQ-05 (sample-pack-baseline): pass=`False`, score=`0.1237`, latency_ms=`4045.536`
  required_hits=`0/4`, any_hits=`0/4`, support=`supported`, citations=`2`, source_coverage=`1.0`
  answer_preview=`제공된 문서에서 확인되지 않습니다.`

### ollama:qwen3.5:9b-nvfp4
- GQ-05 (sample-pack-baseline): pass=`False`, score=`0.925`, latency_ms=`3091.401`
  required_hits=`4/4`, any_hits=`3/4`, support=`supported`, citations=`2`, source_coverage=`1.0`
  answer_preview=`제공된 문서에서 확인되지 않습니다. 프랑스의 에콜 폴리테크니크는 국가 위기 상황에서 실용적 기술 인재를 양성하는 모델로 소개되어 있으나, 독일의 훔볼트 대학에 대한 구체적인 인재 양성 방식이나 두 기관 간의 비교 내용은 문서에 포함되어 있지 않습니다.`
