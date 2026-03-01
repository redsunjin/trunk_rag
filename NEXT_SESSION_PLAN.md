# doc_rag 다음 세션 계획 / 세션 핸드오버 (2026-02-28 기준)

기준 문서:
- `SPEC.md`
- `README.md`
- `TODO.md`
- `docs/PREPROCESSING_RULES.md`
- `docs/VECTORSTORE_POLICY.md`
- `docs/COLLECTION_ROUTING_POLICY.md`
- `docs/reports/MULTI_COLLECTION_POC_REPORT_2026-02-26.md`
- `docs/reports/TOKEN_CHUNKING_POC_REPORT_2026-02-27.md`
- `docs/reports/QUERY_E2E_P95_REPORT_2026-02-27.md`
- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- `docs/NEXT_SESSION_CONTEXT_2026-02-28.md`
- `docs/WIP_SNAPSHOT_2026-02-28.md`

작성 목적:
- 세션 단절 이후에도 동일 기준으로 재진입할 수 있도록 상태를 단일 문서로 고정
- 완료/미완료 범위를 재정렬하고, 다음 작업 우선순위를 명확화

## 0. 2026-02-28 세션 업데이트 (이번 세션 반영)

완료 항목:
1. P3-Prep 백엔드 분해 완료
- `app_api.py`를 조립 계층으로 축소
- 신규 모듈 추가:
  - `core/settings.py`, `core/errors.py`, `core/http.py`
  - `services/runtime_service.py`, `services/collection_service.py`, `services/index_service.py`, `services/query_service.py`, `services/upload_service.py`
  - `api/schemas.py`, `api/routes_query.py`, `api/routes_system.py`, `api/routes_upload.py`, `api/routes_docs_ui.py`

2. P3-Prep 프론트 분해 완료
- `web/index.html`, `web/admin.html` inline script 제거
- 신규 모듈 추가:
  - `web/js/shared.js`
  - `web/js/app_page.js`
  - `web/js/admin_page.js`
- JS 제공 엔드포인트 추가: `GET /js/{file_name}`

3. 테스트 구조 분해 완료
- API 테스트를 기능군 단위로 분리:
  - `tests/api/test_system_api.py`
  - `tests/api/test_query_api.py`
  - `tests/api/test_upload_api.py`
- 회귀 테스트: `.venv\Scripts\python.exe -m pytest -q`
- 결과: `24 passed`

4. 스냅샷 문서 고정
- `docs/WIP_SNAPSHOT_2026-02-28.md` 추가

## 1. 현재 상태 (핵심)

정량 스냅샷:
- `app_api.py`: 160 lines
- `web/index.html`: 156 lines
- `web/admin.html`: 70 lines
- `web/js/app_page.js`: 396 lines
- `web/js/admin_page.js`: 249 lines
- 전체 테스트: `24 passed`

판단:
- P3-Prep 게이트(`app_api.py <= 350`, inline script 외부화, 회귀 통과)는 충족됨.
- 다음 우선순위는 성능/품질 파라미터 재탐색 + P3 기능 착수로 이동.

## 2. 현재 남은 작업 범위 (핵심)

즉시 진행 대상 (다음 세션 1순위):
1. 토큰 모드 파라미터 재탐색(예: chunk_size/overlap 조정)
2. `/query` 품질/지연 균형 프로파일 재탐색(`DOC_RAG_OLLAMA_NUM_PREDICT`, `DOC_RAG_MAX_CONTEXT_CHARS`)
3. 벤치 결과(JSON/리포트) 갱신 및 운영 기본값 재확정

후속 대상 (P3):
1. 데스크톱 래핑(Electron/Tauri) PoC
2. 문서 업로드/갱신 관리자 워크플로우 설계(운영 절차 중심)

## 3. 다음 세션 우선순위 (실행 순서)

### A. 성능/품질 재탐색
1. 토큰 청킹 파라미터 실험(`scripts/benchmark_token_chunking.py`)
2. `/query` E2E 재측정(`scripts/benchmark_query_e2e.py`)
3. 단일/다중 컬렉션 검색 비용 재확인(`scripts/benchmark_multi_collection.py`)

### B. 운영 기본값 확정
1. `.env.example` 기본값/권장값 갱신
2. `README.md`, `SPEC.md` 동기화
3. 리포트 요약(`docs/reports/*`) 갱신

### C. P3 기능 착수
1. 데스크톱 래핑(Electron/Tauri) PoC
2. 업로드/갱신 관리자 워크플로우 상세 설계

## 4. 세션 시작 체크리스트 (핸드오버용)

1. `git status --short`로 작업트리 확인
2. `.venv\Scripts\python.exe -m pytest -q`
3. `run_doc_rag.bat` 실행 후 `/intro`, `/app`, `/admin` 로딩 확인
4. `GET /health` 확인(벡터 수/auto_approve/pending/chunking_mode 확인)
5. `POST /reindex` 1회 실행(응답 내 `validation.summary_text` 확인)
6. `/query` 샘플 질의(단일 + 다중 컬렉션) 확인

## 5. git worktree + agent 병렬 도입 계획 (권장)

결론:
- P3-Prep 분해가 완료되어, 다음 단계부터는 P3 기능 트랙 병렬화 가치가 높아짐.

도입 단계:
1. Stage A (파일럿 2트랙)
- Track-1(Core): 성능/품질 파라미터 실험 + 리포트
- Track-2(Product): 데스크톱 PoC + 관리자 워크플로우 설계

2. Stage B (확장 3트랙)
- Track-1: 데스크톱 래핑 구현
- Track-2: 업로드/갱신 운영 정책/플로우
- Track-3: 회귀 QA/문서 동기화

## 6. 리스크 및 확인 포인트

1. 다중 컬렉션은 커버리지 이점이 있으나 p95 지연 상승 리스크 유지
2. 벤치 환경에 따라 LLM 응답 시간이 크게 변동될 수 있음
3. 서비스 분해 후 monkeypatch 경로가 바뀌었으므로 신규 테스트 작성 시 모듈 경로 준수 필요

## 7. 다음 커밋 목표 (권장)

1. `refactor(api): split app_api into routers/services/core`
2. `refactor(web): move inline scripts to web/js modules`
3. `test(api): split smoke tests by domain`
4. `docs(plan): sync plan/todo after p3-prep completion`
