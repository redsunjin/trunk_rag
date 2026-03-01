# WIP Snapshot (2026-02-28)

목적:
- 세션 단절 시에도 동일 기준으로 재진입할 수 있도록 현재 작업 상태를 고정한다.
- P3-Prep(구조 분해) 착수 전 기준선을 명시한다.

## 1) 현재 브랜치/작업트리

- branch: `main`
- 상태: 대규모 WIP 변경(기능 + 문서 + 벤치 산출물 + 테스트)이 한 작업트리에 동시 존재
- 참고: `git status -sb`, `git diff --stat`

## 2) 기준선 테스트

- 실행: `.venv\Scripts\python.exe -m pytest -q`
- 결과: `24 passed`

## 3) 주요 병목 파일(분해 대상)

- `app_api.py` (단일 파일 다중 책임)
- `web/index.html` (inline script 과다)
- `web/admin.html` (inline script 과다)
- `tests/test_api_smoke.py` (단일 파일 과밀)

## 4) 즉시 수행 순서 (P3-Prep)

1. 백엔드 분해: `app_api.py` -> `core/`, `services/`, `api/routes_*`
2. 프론트 분해: `web/index.html`, `web/admin.html` -> `web/js/*`
3. 테스트 분해: `tests/test_api_smoke.py` -> `tests/api/*`
4. 회귀 확인: `pytest -q`
5. 문서 동기화: `TODO.md`, `NEXT_SESSION_PLAN.md`, 리포트 수치 갱신

## 5) 운영 메모

- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`의 라인 수치는 재측정 후 갱신 필요
- 새 문서 `W3_006_RAG_기술경험_참고문서.md`는 현재 코드에서 참조되지 않음(분류 필요)
