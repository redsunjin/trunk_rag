# 토큰 청킹 PoC 벤치 메모 (2026-02-27)

목적:
- `char` 기본 청킹과 `token` 청킹의 분할 단계 비용/분포를 비교한다.
- 운영 기본값(`char`) 유지 여부와 `token` 옵션 노출 범위를 결정한다.

## 1) 측정 조건

- 스크립트: `scripts/benchmark_token_chunking.py`
- 실행 명령:
  - `.venv\Scripts\python.exe scripts\benchmark_token_chunking.py --rounds 5 --output docs\reports\token_chunking_benchmark_2026-02-27.json`
- 입력 문서: `eu_summry.md`, `fr.md`, `ge.md`, `it.md`, `uk.md`
- 파라미터:
  - `chunk_size=800`
  - `chunk_overlap=120`
  - `token_encoding=cl100k_base`
- 라운드: 5회

주의:
- 본 벤치는 청킹 단계만 측정한다.
- 임베딩 생성/벡터 적재/LLM 응답 시간은 제외된다.

## 2) 결과 요약

| mode | chunk_count | split_time_avg_ms | split_time_p95_ms | token_length_avg | token_length_p95 |
|---|---:|---:|---:|---:|---:|
| char | 37 | 10.243 | 13.828 | 657.081 | 774.2 |
| token | 37 | 66.640 | 74.629 | 658.270 | 777.2 |

부가 관찰:
- 두 모드 모두 청크 수(`37`)와 source별 분포(`9/7/7/7/7`)는 동일했다.
- 토큰 길이 분포도 유사했다(평균 약 657~658).
- 동일 파라미터에서 `token` 모드는 분할 시간 p95가 `char` 대비 약 `+439.7%` 증가했다.

## 3) 해석

1. 현재 데이터셋/파라미터에서는 `token` 모드의 즉시 이득이 크지 않다.
2. 토큰 길이 제어 정밀도는 얻을 수 있지만, 분할 단계 비용이 유의미하게 증가한다.
3. 따라서 운영 기본값은 `char` 유지가 합리적이다.

## 4) 운영 권고 (이번 세션 반영)

1. 기본값: `char` 유지
2. 옵션: `DOC_RAG_CHUNKING_MODE=token`으로 실험 가능하게 유지
3. 관측: `/health` 응답에 `chunking_mode` 노출해 현재 모드 확인

## 5) 후속 작업

1. 토큰 모드에서 `chunk_size/chunk_overlap` 재탐색(예: 700/80, 900/120)
2. `/query` E2E(LLM 포함) 기준 p95 비교 추가
3. 데이터셋이 커질 때(벡터 수 증가) 모드별 품질 차이 재검증
