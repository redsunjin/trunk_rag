# Ollama Gemma4 Perf Check (2026-04-05)

## 목적
- 로컬 Ollama 경로에서 `gemma4:e4b`의 직접 생성 처리량과 `trunk_rag` 실제 `/query` gate 성능을 확인한다.
- 같은 세션에서 `llama3.1:8b`와 비교해 "지연"과 "answer-level gate"를 함께 본다.

## 실행 환경
- Ollama base URL: `http://localhost:11434`
- 앱 base URL: `http://127.0.0.1:8000`
- 로컬 모델 목록 확인: `ollama list` 기준 `gemma4:e4b`, `llama3.1:8b` 모두 사용 가능

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
```

## 직접 Ollama 처리량

| model | avg wall ms | p95 wall ms | avg eval tps | assessment |
| --- | ---: | ---: | ---: | --- |
| `gemma4:e4b` | `8823.794` | `10493.026` | `40.088` | `borderline` |
| `llama3.1:8b` | `5997.817` | `7780.151` | `34.515` | `borderline` |

해석:
- `gemma4:e4b`는 직접 생성 토큰 처리량 자체는 `llama3.1:8b`보다 높게 나왔다.
- 다만 wall time은 더 길었고, 두 모델 모두 이 저장소 기준 평가는 `promising`이 아니라 `borderline`으로 분류됐다.

## `/query` gate 결과

### gemma4 단계별 결과

| phase | ready | pass_rate | avg latency ms | p95 latency ms | avg weighted score |
| --- | --- | ---: | ---: | ---: | ---: |
| cold-start first gate | `false` | `0.6667` | `6777.255` | `11398.822` | `0.6503` |
| warm gate before prompt fix | `false` | `0.6667` | `3948.283` | `4640.512` | `0.6503` |
| warm gate after prompt/postprocess fix | `false` | `1.0` | `4328.464` | `4831.276` | `0.8933` |

해석:
- first gate는 앱 첫 질의라 embedding/model warm-up 비용이 섞였다.
- prompt/postprocess 보강 전에는 warm 상태에서도 `GQ-20` reasoning leakage 때문에 `2/3 pass`에 머물렀다.
- 보강 후에는 warm 상태 `generic-baseline`이 `3/3 pass`로 올라갔다.
- 다만 `check_ops_baseline_gate.py`의 전체 `ready`는 answer eval뿐 아니라 runtime profile도 함께 보기 때문에, `gemma4:e4b`가 아직 `experimental`인 현재 정책상 계속 `false`로 남는다.

### 같은 세션 비교값

| model | ready | pass_rate | avg latency ms | p95 latency ms | avg weighted score |
| --- | --- | ---: | ---: | ---: | ---: |
| `gemma4:e4b` after fix | `false` | `1.0` | `4328.464` | `4831.276` | `0.8933` |
| `llama3.1:8b` | `false` | `0.3333` | `4641.541` | `5278.185` | `0.6994` |

## 실패 패턴

### `gemma4:e4b`
- 초기 실패 원인은 `GQ-20`에서 나온 `"Here's a thinking process to construct the answer:"` reasoning leakage였다.
- `services/query_service.py`의 prompt 금지 문구와 reasoning pattern을 보강한 뒤에는 같은 질문이 정상 답변으로 바뀌었다.
- 보강 후 warm 상태 `generic-baseline`은 `3/3 pass`였다.

### `llama3.1:8b`
- `GQ-19`, `GQ-20` 실패
- 주요 원인은 길이/완결성 부족이었다.
- `GQ-21`만 pass했다.

## 결론
- `gemma4:e4b`는 warm 상태 `/query` 지연과 answer-level gate만 보면 이번 세션에서 `generic-baseline 3/3 pass`까지 올라왔다.
- reasoning leakage blocker는 prompt/postprocess 보강으로 해소됐다.
- 그럼에도 전체 gate `ready`는 `runtime_profile=experimental` 때문에 여전히 `false`다.
- 즉, 현재 판단은 "`gemma4:e4b`는 release-ready는 아니지만, 실측상 유의미한 local candidate"다.
- 후속 작업은 verified 기본값을 바꾸기보다 `gemma4:e4b`를 experimental candidate로 공식 메모에 올릴지, 혹은 runtime profile 정책에 별도 후보 분류를 둘지 판단하는 것이다.
