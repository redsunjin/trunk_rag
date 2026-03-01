# Next Session Context (2026-02-28)

## 현재 결론 요약

1. P2-Next의 `/query` 성공 p95 재계측은 완료됨.
2. P3-Prep(코드베이스 효율화 분해)는 완료됨.
3. 다음 단계는 성능/품질 파라미터 재탐색 + P3 기능 착수.

현재 구조 요약:
- `app_api.py` (160 lines, 조립 계층)
- 라우트/서비스/코어 분리 완료(`api/*`, `services/*`, `core/*`)
- 프론트 inline script 외부화 완료(`web/js/*`)
- API 테스트 분리 완료(`tests/api/*`)
- 회귀 테스트 `24 passed`

참조:
- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- `NEXT_SESSION_PLAN.md`
- `TODO.md`
- `docs/WIP_SNAPSHOT_2026-02-28.md`

## 다음 세션 첫 30분 액션

1. 상태 점검
```powershell
git status --short
.venv\Scripts\python.exe -m pytest -q
```

2. 런타임/품질 지표 재측정
```powershell
.venv\Scripts\python.exe scripts\benchmark_token_chunking.py --rounds 5
.venv\Scripts\python.exe scripts\benchmark_query_e2e.py --base-url http://127.0.0.1:8000 --rounds 2 --warmup 1
```

3. 기본값 재확정 대상
- `DOC_RAG_OLLAMA_NUM_PREDICT`
- `DOC_RAG_MAX_CONTEXT_CHARS`
- 필요 시 `DOC_RAG_QUERY_TIMEOUT_SECONDS`

## 다음 세션 완료 기준

1. 파라미터 후보별 벤치 수치(JSON + 리포트) 갱신
2. 운영 기본값 확정(`.env.example`, `README.md`, `SPEC.md` 동기화)
3. P3 기능 착수 항목(데스크톱 PoC 또는 관리자 워크플로우) 1개 이상 시작

## 작업 시 주의

1. API 응답 스키마/헤더 계약 유지
2. 라우트/서비스 경계는 유지하고 기능 추가는 해당 모듈에만 반영
3. 테스트 monkeypatch는 `api.routes_*` / `services.*` 실제 경로 기준으로 작성
