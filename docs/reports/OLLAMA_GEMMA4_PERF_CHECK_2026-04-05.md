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

### warm 상태 기준 비교

| model | ready | pass_rate | avg latency ms | p95 latency ms | avg weighted score |
| --- | --- | ---: | ---: | ---: | ---: |
| `gemma4:e4b` | `false` | `0.6667` | `3948.283` | `4640.512` | `0.6503` |
| `llama3.1:8b` | `false` | `0.3333` | `4641.541` | `5278.185` | `0.6994` |

### gemma4 cold-start 참고값
- 첫 `gemma4:e4b` gate는 앱 첫 질의라 embedding/model warm-up 비용이 섞였다.
- 이 첫 측정은 `pass_rate=0.6667`, `avg_latency_ms=6777.255`, `p95_latency_ms=11398.822`, `avg_weighted_score=0.6503`였다.
- 같은 세션 warm 재실행 결과가 위 표의 수치다.

## 실패 패턴

### `gemma4:e4b`
- `GQ-20` 실패
- 응답이 `"Here's a thinking process to construct the answer:"`로 끝나 reasoning leakage가 그대로 노출됐다.
- 나머지 `GQ-19`, `GQ-21`은 pass했다.

### `llama3.1:8b`
- `GQ-19`, `GQ-20` 실패
- 주요 원인은 길이/완결성 부족이었다.
- `GQ-21`만 pass했다.

## 결론
- `gemma4:e4b`는 warm 상태 `/query` 지연만 보면 이번 세션에서 `llama3.1:8b`보다 빠르게 나왔다.
- 하지만 `generic-baseline`은 `2/3 pass`에 그쳐 release gate 기준으로는 아직 `ready`가 아니다.
- 핵심 blocker는 `GQ-20`에서 드러난 reasoning leakage다.
- 같은 세션에서 `llama3.1:8b`도 `1/3 pass`만 나왔기 때문에, 이번 단일 실측만으로 기존 verified 운영 프로파일 정책을 바꾸지는 않는다.
- 후속 작업은 `gemma4:e4b`를 candidate로 두고, `GQ-20` 계열 질문에서 reasoning leakage를 더 강하게 제거하거나 prompt contract를 보강해 재측정하는 것이다.
