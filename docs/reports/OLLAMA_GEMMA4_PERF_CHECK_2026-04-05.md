# Ollama Gemma4 Perf Check (2026-04-05)

## 목적
- 로컬 Ollama 경로에서 `gemma4:e4b`의 직접 생성 처리량과 `trunk_rag` 실제 `/query` gate 성능을 확인한다.
- 같은 세션에서 `llama3.1:8b`와 현재 설치된 더 작은 후보 `qwen3.5:4b-nvfp4`를 비교해 "지연"과 "answer-level gate"를 함께 본다.

## 실행 환경
- Ollama base URL: `http://localhost:11434`
- 앱 base URL: `http://127.0.0.1:8000`
- 로컬 모델 목록 확인: `ollama list` 기준 `gemma4:e4b`, `llama3.1:8b`, `qwen3.5:4b-nvfp4` 사용 가능

## 실행 명령
```bash
./.venv/bin/python scripts/diagnose_ollama_runtime.py \
  --model gemma4:e4b \
  --prompt "숫자 1부터 80까지를 쉼표로 구분해 한 줄로만 출력하세요." \
  --repeat 3 \
  --timeout-seconds 120 \
  --json

./.venv/bin/python scripts/diagnose_ollama_runtime.py \
  --model llama3.1:8b \
  --prompt "숫자 1부터 80까지를 쉼표로 구분해 한 줄로만 출력하세요." \
  --repeat 3 \
  --timeout-seconds 120 \
  --json

./.venv/bin/python app_api.py

./.venv/bin/python scripts/check_ops_baseline_gate.py \
  --base-url http://127.0.0.1:8000 \
  --llm-provider ollama \
  --llm-model gemma4:e4b \
  --llm-base-url http://localhost:11434 \
  --json

./.venv/bin/python scripts/check_ops_baseline_gate.py \
  --base-url http://127.0.0.1:8000 \
  --llm-provider ollama \
  --llm-model llama3.1:8b \
  --llm-base-url http://localhost:11434 \
  --json

./.venv/bin/python scripts/check_ops_baseline_gate.py \
  --base-url http://127.0.0.1:8000 \
  --llm-provider ollama \
  --llm-model qwen3.5:4b-nvfp4 \
  --llm-base-url http://localhost:11434 \
  --json
```

## 직접 Ollama 처리량

| model | avg wall ms | p95 wall ms | avg eval tps | assessment |
| --- | ---: | ---: | ---: | --- |
| `gemma4:e4b` | `8823.794` | `10493.026` | `40.088` | `borderline` |
| `llama3.1:8b` | `5997.817` | `7780.151` | `34.515` | `borderline` |

해석:
- `gemma4:e4b`는 직접 생성 토큰 처리량 자체는 `llama3.1:8b`보다 높게 나왔다.
- 다만 wall time은 더 길었고, 두 모델 모두 이 저장소 기준 평가는 `promising`이 아니라 `borderline`으로 분류됐다.
- 같은 prompt로 `qwen3.5:4b-nvfp4` direct diagnose도 시도했지만 `--timeout-seconds 120` 안에 응답을 돌려주지 못해 raw 처리량 비교 표에는 넣지 않았다.

## `/query` gate 결과

### gemma4 단계별 결과

| phase | ready | pass_rate | avg latency ms | p95 latency ms | avg weighted score |
| --- | --- | ---: | ---: | ---: | ---: |
| cold-start first gate | `false` | `0.6667` | `6777.255` | `11398.822` | `0.6503` |
| warm gate before prompt fix | `false` | `0.6667` | `3948.283` | `4640.512` | `0.6503` |
| warm gate after prompt/postprocess fix | `false` | `1.0` | `4328.464` | `4831.276` | `0.8933` |
| warm gate revalidation | `false` | `1.0` | `3890.691` | `4283.135` | `0.8933` |
| fresh app verified default gate | `true` | `1.0` | `7700.859` | `13043.855` | `0.9067` |
| fresh app verified gate after light hybrid merge | `true` | `1.0` | `6685.677` | `11030.653` | `0.9067` |
| fresh app verified gate after coverage rerank | `true` | `1.0` | `4329.476` | `4411.131` | `0.9200` |

해석:
- first gate는 앱 첫 질의라 embedding/model warm-up 비용이 섞였다.
- prompt/postprocess 보강 전에는 warm 상태에서도 `GQ-20` reasoning leakage 때문에 `2/3 pass`에 머물렀다.
- 보강 후에는 warm 상태 `generic-baseline`이 `3/3 pass`로 올라갔다.
- 이후 runtime policy를 `gemma4:e4b + DOC_RAG_QUERY_TIMEOUT_SECONDS=30` verified 기본값으로 승격한 뒤에는, fresh app 기준 full gate도 `ready=true`로 통과했다.
- 같은 verified runtime에서 경량 hybrid candidate merge를 추가한 뒤에도 score는 유지됐고, fresh app 기준 full gate latency는 더 낮아졌다.
- 이어서 multi-collection coverage rerank를 추가한 뒤에는 `GQ-21` 상위 context가 `fr -> ge -> fr ...`로 재정렬됐고, full gate의 latency/score가 모두 더 좋아졌다.

### 같은 세션 비교값

| model | ready | pass_rate | avg latency ms | p95 latency ms | avg weighted score |
| --- | --- | ---: | ---: | ---: | ---: |
| `gemma4:e4b` verified default gate | `true` | `1.0` | `7700.859` | `13043.855` | `0.9067` |
| `qwen3.5:4b-nvfp4` | `false` | `0.6667` | `2671.665` | `3770.352` | `0.9022` |
| `llama3.1:8b` | `false` | `0.3333` | `4641.541` | `5278.185` | `0.6994` |

## 실패 패턴

### `gemma4:e4b`
- 초기 실패 원인은 `GQ-20`에서 나온 `"Here's a thinking process to construct the answer:"` reasoning leakage였다.
- `services/query_service.py`의 prompt 금지 문구와 reasoning pattern을 보강한 뒤에는 같은 질문이 정상 답변으로 바뀌었다.
- 보강 후 warm 상태 `generic-baseline`은 재측정에서도 `3/3 pass`였다.

### `qwen3.5:4b-nvfp4`
- 같은 세션 warm 상태 gate는 `avg_latency_ms=2671.665`, `p95_latency_ms=3770.352`로 더 빨랐지만 `2/3 pass`에 머물렀다.
- 실패 케이스는 `GQ-21`이었고, multi-collection 질문에서 "문서에 직접 비교가 없다"는 답을 너무 짧게 끝내 `min_chars_ratio=0.9333`, `weighted_score=0.8266`으로 탈락했다.
- `GQ-19`는 pass했지만 응답 말미에 `</final_answer` 조각이 남아, 작은 모델 쪽 출력 안정성이 아직 거칠다는 신호도 보였다.

### `llama3.1:8b`
- `GQ-19`, `GQ-20` 실패
- 주요 원인은 길이/완결성 부족이었다.
- `GQ-21`만 pass했다.

## 결론
- `gemma4:e4b`는 warm 상태 재측정에서 `generic-baseline 3/3 pass`, `avg_latency_ms=3890.691`, `p95_latency_ms=4283.135`를 유지했고, verified 기본값 승격 후 fresh app full gate도 `ready=true`, `avg_latency_ms=7700.859`, `p95_latency_ms=13043.855`로 통과했다.
- 이후 경량 hybrid candidate merge를 더한 fresh app full gate도 `ready=true`, `avg_latency_ms=6685.677`, `p95_latency_ms=11030.653`, `avg_weighted_score=0.9067`로 유지돼 1차 채택 후보로 볼 수 있다.
- 이후 cost trace 보강으로 `hybrid_scan_doc_count`, `hybrid_skipped_collections`가 추가돼 큰 컬렉션에서 `collection_too_large` skip이 실제로 보이는지 직접 추적할 수 있게 됐다.
- trace 보강 뒤 재실측에서도 full gate는 `ready=true`, `avg_latency_ms=7220.103`, `p95_latency_ms=12405.726`, `avg_weighted_score=0.9067`로 유지됐다.
- 이어서 coverage rerank 비교에서는 `ready=true`, `avg_latency_ms=4329.476`, `p95_latency_ms=4411.131`, `avg_weighted_score=0.9200`로 추가 개선이 확인됐다.
- reasoning leakage blocker는 prompt/postprocess 보강으로 해소됐다.
- `qwen3.5:4b-nvfp4`는 더 작고 더 빨랐지만, 이번 세션에서는 `GQ-21` 길이 부족 때문에 `2/3 pass`였다.
- 현재 판단은 "`gemma4:e4b`는 verified local default", "`qwen3.5:4b-nvfp4`는 latency 우선 experimental fallback" 쪽이다.
- 현재 coverage rerank 후보는 같은 `generic-baseline`에서 `GQ-21` score를 `0.88 -> 0.92`로 높였고, fresh gate 기준 `avg_latency_ms`와 `p95_latency_ms`도 모두 낮췄다.
- `2026-04-05` closeout review 기준으로 현재 기본 경로는 `mmr+light_hybrid+lexical_boost+coverage_rerank` 조합으로 유지한다.
- 다음 작업은 `LOOP-010` 기준으로 existing chunk metadata만으로 적용 가능한 contextual retrieval 후보를 검토하는 것이다.
