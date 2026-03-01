# doc_rag TODO (Next Session Start)

목적:
- 다음 세션에서 바로 착수 가능한 작업 목록을 고정한다.
- `P0`를 먼저 완료하고 이후 `P1`로 넘어간다.

참조:
- `NEXT_SESSION_PLAN.md`
- `SPEC.md`
- `docs/PREPROCESSING_RULES.md`
- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- `docs/NEXT_SESSION_CONTEXT_2026-02-28.md`

## P0 (즉시 착수)

### 1) API/프론트 최소 회귀 테스트 추가
- [x] API 테스트 생성 및 분리 (`tests/test_api_smoke.py` -> `tests/api/test_*.py`)
- [x] `tests/e2e/test_web_flow_playwright.py` 생성
- [x] 케이스:
  - [x] `GET /health` == 200
  - [x] `GET /rag-docs` == 200
  - [x] `GET /rag-docs/{doc_name}` 성공/404 케이스
  - [x] `POST /reindex` == 200 (monkeypatch 기반)
  - [x] `POST /query` 성공/실패 케이스
- [x] 실행 명령 정리 (`pytest` 기준)

완료 기준:
- 테스트가 로컬에서 통과하고, 실패 시 원인이 로그로 구분된다.

### 2) `/query` 에러 처리 표준화
- [x] 에러 응답 포맷 통일:
  - [x] `code`
  - [x] `message`
  - [x] `hint` (가능 시)
- [x] 주요 실패 시나리오 반영:
  - [x] 벡터스토어 비어 있음
  - [x] LLM 연결 실패 (provider/base_url/api_key)
  - [x] 타임아웃
  - [x] 잘못된 요청 파라미터

완료 기준:
- 프론트에서 사용자에게 에러 원인을 명확히 안내할 수 있다.

### 3) 문서 전처리 규칙 초안 확정
- [x] `docs/PREPROCESSING_RULES.md` 생성
- [x] 규칙 정의:
  - [x] 허용 헤더(`##`, `###`, `####`)
  - [x] 제목/본문 최소 길이
  - [x] 금지 패턴(빈 섹션, 중복 헤더 등)
  - [x] 메타데이터 최소 항목(`source`, `country`, `doc_type`)
- [x] 샘플 입력/출력 예시 1세트 작성

완료 기준:
- 누구나 동일 규칙으로 md 품질 점검 가능하다.

## P2 (후속)

- [ ] 데스크톱 래핑(Electron/Tauri) PoC
- [ ] 문서 업로드/갱신 관리자 워크플로우 설계

## P3-Prep (코드베이스 효율화 게이트)

- [x] 코드베이스 효율화 점검 리포트 작성
  - [x] `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- [x] 백엔드 분해 1차 (`app_api.py` 책임 분리)
  - [x] 라우트 모듈 분리(`api/routes_*.py`)
  - [x] 서비스 모듈 분리(`services/*.py`)
  - [x] 설정/에러 모듈 분리(`core/settings.py`, `core/errors.py`)
  - [x] 목표: `app_api.py <= 350 lines`
- [x] 프론트 분해 1차 (inline script 외부화)
  - [x] `web/js/shared.js` 생성(공통 유틸)
  - [x] `web/js/app_page.js` 생성(`index.html` 로직 이동)
  - [x] `web/js/admin_page.js` 생성(`admin.html` 로직 이동)
  - [x] 목표: `index/admin` inline script 최소화
- [x] 테스트 구조 정리
  - [x] `tests/api/test_system_api.py`, `tests/api/test_query_api.py`, `tests/api/test_upload_api.py` 분리
  - [x] 회귀 테스트 실행 및 통과(`pytest -q`)

완료 기준:
- [x] 대형 단일 파일 중심 개발 병목이 완화된다.
- [x] 기능 동작 동일성 유지(회귀 테스트 통과).
- [x] 다음 P3 기능(데스크톱 PoC/관리 워크플로우) 작업 충돌이 감소한다.

## P2-Next (2026-02-27 진행 결과)

- [x] 토큰 청킹 실험 스크립트 추가 (`scripts/benchmark_token_chunking.py`)
- [x] 토큰 청킹 비교 결과 기록
  - [x] `docs/reports/token_chunking_benchmark_2026-02-27.json`
  - [x] `docs/reports/TOKEN_CHUNKING_POC_REPORT_2026-02-27.md`
- [x] 청킹 모드 옵션화 (`char` 기본, `token` 옵션)
  - [x] `DOC_RAG_CHUNKING_MODE`
  - [x] `DOC_RAG_CHUNK_TOKEN_ENCODING`
- [x] FastAPI startup 이벤트를 lifespan으로 전환 (`app_api.py`)
- [x] 운영 문서 갱신 (`README.md`, `.env.example`, `NEXT_SESSION_PLAN.md`)
- [x] 회귀 테스트 통과 (`24 passed`)
- [x] `/query` end-to-end(LLM 포함) p95 계측 자동화
  - [x] 스크립트: `scripts/benchmark_query_e2e.py`
  - [x] 1차 실측 결과 JSON/보고서 작성
    - [x] `docs/reports/query_e2e_benchmark_2026-02-27.json`
    - [x] `docs/reports/QUERY_E2E_P95_REPORT_2026-02-27.md`
  - [x] LLM 연결 정상화 후 성공 응답 기준 p95 재계측

## 병렬 자동화 도입 (git worktree + agent)

도입 트리거:
- [ ] `NEXT_SESSION_PLAN.md`의 `P2-Next` 착수 시점에 Stage A 시작

### Stage A (파일럿, 2트랙)
- [ ] Track-1(Core): 토큰 기준 청킹 검증 전담
- [ ] Track-2(Ops): 코드베이스 효율화 분해 + QA/문서 정리 전담
- [ ] 동일 파일 동시 수정 금지 원칙 적용(`app_api.py` 충돌 회피)
- [ ] worktree 생성
  - [ ] `git worktree add ..\doc_rag-wt-core -b feat/p2-token-chunking`
  - [ ] `git worktree add ..\doc_rag-wt-ops -b chore/p3-efficiency-split`

완료 기준:
- [ ] Track-1/2 각각 독립 PR(또는 커밋 단위)로 병합 가능 상태
- [ ] 전체 회귀 테스트 통과

### Stage B (확장, P3 3트랙)
- [ ] Track-1: 데스크톱 래핑 PoC
- [ ] Track-2: 업로드/갱신 관리자 워크플로우 설계
- [ ] Track-3: QA/문서 업데이트 전담

완료 기준:
- [ ] 각 트랙 산출물이 충돌 없이 병합
- [ ] 운영/핸드오버 문서 동기화 완료

### Stage C (병합 규칙)
- [ ] 병합 순서: Core -> QA -> Docs
- [ ] 병합 전 `pytest -q` 실행
- [ ] 병합 후 `NEXT_SESSION_PLAN.md`, `TODO.md` 체크박스 즉시 갱신

## Session Start Checklist

- [ ] `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md` 확인
- [ ] `run_doc_rag.bat` 실행
- [ ] `/health` 확인
- [ ] `/reindex` 1회 실행
- [ ] `/query` 샘플 질의 2~3개 확인
- [x] P0의 1번부터 순차 수행

참고:
- 환경별로 `.venv`에 `pytest`/`playwright`가 누락될 수 있다.
- 누락 시 `requirements-dev.txt` 설치 후 테스트 실행/통과 여부를 최종 확인한다.

## P1 (다음 세션 핵심)

상태:
- [x] P1 핵심 항목 1~5 1차 구현 완료 (2026-02-24)

### 1) 전처리 가이드 제공(문서 템플릿 중심)
- [x] `docs/PREPROCESSING_PROMPT_TEMPLATE.md` 생성
- [x] `docs/PREPROCESSING_METADATA_SCHEMA.json` 생성
- [x] 전처리 산출물 예시(`.md` + metadata) 1세트 정리

완료 기준:
- 외부 전처리 담당자가 동일 형식으로 산출물을 만들 수 있다.

### 2) 컬렉션 선택/라우팅 기반 사용자 UI
- [x] `/intro`에서 사용자/관리자 진입 분기 UI 추가
- [x] 기존 채팅 UI에 컬렉션 선택 드롭다운 추가
- [x] `/query` 요청 시 선택한 컬렉션 전달

완료 기준:
- 사용자는 컬렉션 선택 후 기존과 동일한 채팅 흐름으로 질의할 수 있다.

### 3) 관리자 인증 및 요청 승인 흐름
- [x] 관리자 인증코드 기반 진입(초기 MVP) 추가
- [x] 업로드 요청 상태 모델 추가(`pending/approved/rejected`)
- [x] 일반 사용자 업로드 요청 API/UI 추가
- [x] 관리자 승인/반려 API/UI 추가
- [x] 개인 운영용 `auto-approve` 옵션 설계 반영

완료 기준:
- 일반 사용자는 요청만 가능하고, 승인된 문서만 인덱싱된다.

### 4) 등록 시 검증 기능(usable 판정)
- [x] 검증 스크립트/모듈 추가 (`scripts/validate_rag_doc.py` 또는 동등 기능)
- [x] 검증 항목:
  - [x] 헤더 구조(`##`, `###`, `####`)
  - [x] 필수 메타(`source`, `country`, `doc_type`)
  - [x] 최소 길이/빈 섹션
- [x] 결과 출력:
  - [x] `usable=true/false`
  - [x] `reasons[]`

완료 기준:
- 인덱싱 전 문서의 RAG 사용 가능 여부를 자동 판정할 수 있다.

### 5) 벡터스토어 운영 정책 적용
- [x] `docs/VECTORSTORE_POLICY.md` 기준 수치 확정
- [x] 컬렉션당 cap `30k~50k vectors` 확정 (총량 기준 대략 `30M~50M tokens`)
- [x] soft cap/hard cap 초과 시 운영 절차 문서화
- [x] 분야별 컬렉션 분할 정책 반영
- [x] 단순 라우팅 정책 반영(`사용자 선택 -> 키워드 매핑 -> fallback`)
- [x] README/SPEC에 정책 링크 반영

완료 기준:
- 데이터 증가 시 성능/품질 저하 대응 기준이 명시되어 있다.
