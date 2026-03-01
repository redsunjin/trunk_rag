# 코드베이스 효율화 점검 리포트 (2026-02-28)

목적:
- P3 기능 확장 전 유지보수 병목을 줄이기 위한 분해 계획/결과를 기록한다.
- 세션 단절 이후에도 분해 완료 여부를 빠르게 확인할 수 있도록 정량 수치를 고정한다.

## 1) 분해 전/후 스냅샷

분해 전(초기 점검):
- `app_api.py`: 1141+ lines, 다중 책임 집중
- `web/index.html`: 531+ lines (inline script 과다)
- `web/admin.html`: 307+ lines (inline script 과다)
- `tests/test_api_smoke.py`: 단일 파일 과밀

분해 후(2026-02-28 적용 결과):
- `app_api.py`: 160 lines
- `web/index.html`: 156 lines
- `web/admin.html`: 70 lines
- `web/js/app_page.js`: 396 lines
- `web/js/admin_page.js`: 249 lines
- 테스트 분리:
  - `tests/api/test_system_api.py`
  - `tests/api/test_query_api.py`
  - `tests/api/test_upload_api.py`
- 회귀 테스트: `24 passed`

## 2) 적용된 구조

백엔드:
- `api/schemas.py`
- `api/routes_query.py`
- `api/routes_system.py`
- `api/routes_upload.py`
- `api/routes_docs_ui.py`
- `services/runtime_service.py`
- `services/collection_service.py`
- `services/index_service.py`
- `services/query_service.py`
- `services/upload_service.py`
- `core/settings.py`
- `core/errors.py`
- `core/http.py`

프론트:
- `web/js/shared.js`
- `web/js/app_page.js`
- `web/js/admin_page.js`
- JS 파일 서빙: `GET /js/{file_name}`

## 3) 달성 여부 (P3-Prep 게이트)

1. `app_api.py <= 350 lines`: 달성
2. `index/admin` inline script 외부화: 달성
3. 회귀 테스트(`pytest -q`) 통과: 달성
4. 계획 문서 동기화: 진행 중(`TODO.md`, `NEXT_SESSION_PLAN.md` 반영)

## 4) 잔여 리스크

1. 라우트/서비스 분리 후 monkeypatch 대상 경로 변경으로 테스트 작성 시 혼동 가능
2. 성능 지표(p95)는 분해 완료와 별개로 런타임 파라미터 영향이 큼
3. 데스크톱 PoC 착수 시 API 계약 고정 필요

## 5) 다음 액션

1. 토큰 청킹 파라미터 재탐색
2. `/query` 품질/지연 균형 재측정
3. 데스크톱 래핑(Electron/Tauri) PoC 착수
4. 업로드/갱신 관리자 운영 워크플로우 상세화
