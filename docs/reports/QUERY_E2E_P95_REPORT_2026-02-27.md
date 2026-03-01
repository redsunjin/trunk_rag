# `/query` E2E p95 계측 리포트 (2026-02-27)

목적:
- `/query` API의 end-to-end 지연을 시나리오별로 수집한다.
- 단일/다중 컬렉션 비교를 운영 지표로 고정한다.

## 1) 측정 조건

- 스크립트: `scripts/benchmark_query_e2e.py`
- 서버 런타임 설정:
  - `DOC_RAG_QUERY_TIMEOUT_SECONDS=90`
  - `DOC_RAG_OLLAMA_NUM_PREDICT=8`
  - `DOC_RAG_MAX_CONTEXT_CHARS=300`
- 실행 명령:
  - `.venv\Scripts\python.exe scripts\benchmark_query_e2e.py --base-url http://127.0.0.1:8000 --llm-provider ollama --llm-model phi3:mini --llm-base-url http://localhost:11434 --rounds 2 --warmup 1 --query-timeout-seconds 120 --output docs\reports\query_e2e_benchmark_2026-02-27.json`
- 시나리오:
  - `single_all`
  - `single_fr`
  - `dual_fr_ge`
- 질의: 3개, 라운드 2회(시나리오당 6회)

## 2) 측정 결과 요약

| scenario | success_ratio | status_counts | latency_all_avg_ms | latency_all_p95_ms | latency_success_p95_ms |
|---|---:|---|---:|---:|---:|
| single_all | 1.00 | `{"200": 6}` | 21275.364 | 39219.862 | 39219.862 |
| single_fr | 1.00 | `{"200": 6}` | 8994.574 | 10123.842 | 10123.842 |
| dual_fr_ge | 1.00 | `{"200": 6}` | 10073.855 | 11522.943 | 11522.943 |

산출물:
- `docs/reports/query_e2e_benchmark_2026-02-27.json`

## 3) 해석

1. 모든 시나리오에서 성공 응답(`200`) 기준 p95를 확보했다.
2. `single_all` p95가 가장 높고(`39.2s`), 단일 국가/2컬렉션 조회는 약 `10~11.5s` 수준이다.
3. 이번 수치는 응답 길이 제한(`DOC_RAG_OLLAMA_NUM_PREDICT=8`)과 컨텍스트 제한(`DOC_RAG_MAX_CONTEXT_CHARS=300`)을 적용한 운영 프로파일 기준이다.

## 4) 후속 액션

1. 품질/지연 균형점 탐색을 위해 `DOC_RAG_OLLAMA_NUM_PREDICT`, `DOC_RAG_MAX_CONTEXT_CHARS`를 단계적으로 상향 재측정
2. `qwen3:4b` 기준 동일 조건(응답 길이/컨텍스트 제한)으로 비교 벤치 추가
3. 운영 기본값 확정 후 `.env.example`, `README`, `NEXT_SESSION_PLAN.md` 동기화
