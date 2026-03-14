# Query E2E Char vs Token Report (2026-03-14)

## 목적
- `char` 기본 모드와 `token_800_120` 후보를 동일한 로컬 프로파일에서 비교한다.
- `/query` 기본 경로의 p95를 다시 확인하고, 기본 청킹 모드 유지 여부를 판단한다.

## 벤치 프로파일
- 서버: `app_api:app`
- LLM: `ollama` + `llama3.1:8b`
- LLM base URL: `http://127.0.0.1:11434`
- query timeout: `90s`
- `DOC_RAG_OLLAMA_NUM_PREDICT=32`
- `DOC_RAG_MAX_CONTEXT_CHARS=300`
- embedding model: 로컬 경로의 `minishlab/potion-base-4M`
- embedding device: `cpu`
- scenarios: `single_all`, `single_fr`, `dual_fr_ge`
- rounds: `2`
- warmup: `1`

참고:
- 이번 벤치는 공식 기본 스택(`BAAI/bge-m3`, `qwen3:4b`)이 아니라 로컬에서 즉시 사용 가능한 프로파일 기준이다.
- Apple Silicon 환경에서는 local static embedding 모델이 `MPS`에서 `embedding_bag` 미구현에 걸려 `DOC_RAG_EMBEDDING_DEVICE=cpu`를 사용했다.

## 결과 요약

| scenario | char p95 ms | token p95 ms | delta |
| --- | ---: | ---: | ---: |
| `single_all` | `796.635` | `780.400` | `-2.0%` |
| `single_fr` | `1264.958` | `1225.715` | `-3.1%` |
| `dual_fr_ge` | `1249.782` | `1226.340` | `-1.9%` |

세부 JSON:
- `docs/reports/query_e2e_benchmark_2026-03-14.json`
- `docs/reports/query_e2e_benchmark_2026-03-14_token_800_120.json`

## 관찰
1. 이번 프로파일에서는 `token_800_120`이 모든 시나리오에서 소폭 더 빠르다.
2. 차이는 작다. p95 기준 개선폭은 약 `1.9% ~ 3.1%` 수준이다.
3. 단일 전체 컬렉션(`single_all`)이 이번 프로파일에서는 가장 빠르다.
4. `single_fr`, `dual_fr_ge`는 성공률 100%였지만 지연은 `single_all`보다 높았다.

## 결론
- `token_800_120`은 실사용 가능한 후보임이 확인됐다.
- 다만 개선폭이 작고, 이번 측정이 공식 기본 스택이 아닌 대체 로컬 프로파일 기준이므로 운영 기본값은 아직 `char` 유지가 안전하다.
- 다음 결정 게이트는 2가지다:
  - 샘플 질의 2~3개 품질 확인
  - 가능하면 공식 기본 스택 또는 더 가까운 로컬 기본 스택으로 재측정
