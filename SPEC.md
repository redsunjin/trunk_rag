# doc_rag 스펙 문서

## 문서 목적
- 현재까지의 구현 결과를 한 문서로 정리한다.
- 다음 단계의 개발 우선순위를 고정한다.
- 운영 시 필요한 실행/API 기준을 명확히 한다.

## 프로젝트 목표
- 폐쇄망/로컬 환경에서 동작하는 RAG 서버 구축
- 전처리 완료된 `.md` 문서 기반 검색 및 질의응답
- 공통 UI/UX 스타일 재사용으로 서비스 일관성 확보
- 무거운 파이프라인 대신 "가벼운 RAG 런타임" 유지

## 현재 범위
### 포함
- 로컬 문서 로딩: `data/*.md` (현재 샘플 5개 파일)
- 헤더 기반 청킹: `##`, `###`, `####` + 모드(`char` 기본, `token` 옵션)
- 임베딩 + 로컬 벡터스토어: HuggingFace + Chroma
- LLM provider 선택: `ollama`, `lmstudio`, `openai`
- FastAPI 서버 + 브라우저 UI
- `/query` 표준 에러 응답 + 요청 ID 추적
- 컬렉션 라우팅(`collection` 선택 + 키워드 fallback)
- 컬렉션 상태 조회(`/collections`) + cap 사용률
- 등록 전 문서 검증(`usable/reasons/warnings`) 1차 적용
- 업로드 요청/승인 워크플로우(`pending/approved/rejected`) 1차 적용
- `/health` 기반 런타임 기본 LLM 설정 노출
- 기본 모드 UI에서 고급 LLM 설정 기본 숨김
- 빈 인덱스/LLM 연결 오류에 대한 가이드 메시지
- API/프론트 최소 회귀 테스트 체계(pytest + Playwright)
- 전처리 규칙 문서(`docs/PREPROCESSING_RULES.md`)

### 제외(현재 단계)
- 사용자 인증/권한
- 멀티 유저 세션 분리
- 분산/HA 배포
- 문서 업로드 관리자 UI
- 원본 소스 자동 수집/크롤링
- 대규모 자동 전처리(재작성/요약) 파이프라인 내장
- cross-encoder rerank/multi-vector 기본 탑재

## 완료된 작업
### 백엔드
- `GET /health`, `POST /reindex`, `POST /query` 구현
- `GET /collections`, `POST /admin/auth` 구현
- `GET /upload-requests`, `POST /upload-requests` 구현
- `POST /upload-requests/{id}/approve`, `POST /upload-requests/{id}/reject` 구현
- `GET /rag-docs`, `GET /rag-docs/{doc_name}` 구현
- `/query` 표준 실패 응답(`code`, `message`, `hint`, `request_id`, `detail`) 구현
- `/query` 타임아웃 정책(15초, 재시도 없음) 적용
- `/query` 성공/실패 응답에 `X-Request-ID` 헤더 제공
- `/` -> `/intro` 리다이렉트
- `/intro` 인트로 페이지, `/app` 메인 RAG UI 제공
- `/admin` 관리자 상태 페이지 제공(MVP)
- `/styles.css` 경로에서 공통 스타일 제공

### RAG 파이프라인
- Markdown 문서 로딩
- 헤더 기준 분할 + 모드별 분할(`char`/`token`)
- 임베딩 생성(`BAAI/bge-m3`)
- Chroma 인덱싱/조회

### 품질/검증
- API 회귀 테스트: `tests/api/test_system_api.py`
- API 회귀 테스트: `tests/api/test_query_api.py`
- API 회귀 테스트: `tests/api/test_upload_api.py`
- 청킹 모드 테스트: `tests/test_chunking_modes.py`
- 프론트 E2E 테스트: `tests/e2e/test_web_flow_playwright.py`

### LLM 연결
- provider 분기 로직 통합
- 모델/키/베이스 URL 해석 로직 통합

### UI/UX
- 공통 `styles.css` 스타일 패턴을 현재 `web/index.html`에 반영
- 공통 레이아웃 클래스 적용(`app-container`, `sidebar`, `main-content`, `card`)
- 화면 구성: 좌측(설정/헬스/문서목록), 우측(채팅/MD 뷰어)
- 인트로/관리자 페이지 분리(`web/intro.html`, `web/admin.html`)
- 프론트 로직 모듈 분리(`web/js/shared.js`, `web/js/app_page.js`, `web/js/admin_page.js`)
- 메인 UI 기본 모드에서 런타임 기본 LLM 설정 자동 적용
- `고급 설정 펼치기`로 provider/model/base URL/API key 수동 수정
- `vectors=0` 상태에서 `Reindex` 선행 안내
- 업로드 요청에서 `Source Name` optional + 컬렉션 기준 기본값 사용

### 구조 분해(P3-Prep 완료)
- `app_api.py`는 앱 조립/예외 처리 중심으로 축소
- 라우트는 `api/routes_*.py`로 분리
- 서비스 로직은 `services/*.py`로 분리
- 설정/에러/HTTP 유틸은 `core/*.py`로 분리

## 핵심 파일
- `app_api.py`: FastAPI 앱 엔트리포인트와 예외 처리
- `api/routes_*.py`: API/UI 라우팅
- `services/*.py`: 인덱싱/질의/업로드 서비스 계층
- `core/*.py`: 설정/에러/HTTP 공통 계층
- `common.py`: 문서/청킹/임베딩/LLM 공통 유틸
- `scripts/validate_rag_doc.py`: 등록 전 문서 검증
- `build_index.py`: 초기 인덱싱 스크립트
- `web/index.html`: 브라우저 UI
- `web/admin.html`: 관리자 상태 UI
- `web/styles.css`: 공통 스타일
- `web/js/*.js`: 프론트 로직 모듈

## API 계약
### GET `/health`
- 목적: 서버 상태와 벡터 개수 확인
- 응답 예:
```json
{
  "status": "ok",
  "collection_key": "all",
  "collection": "w2_007_header_rag",
  "persist_dir": "C:/.../chroma_db",
  "vectors": 37,
  "auto_approve": false,
  "pending_requests": 2,
  "chunking_mode": "char",
  "query_timeout_seconds": 15,
  "max_context_chars": null,
  "default_llm_provider": "ollama",
  "default_llm_model": "qwen3:4b",
  "default_llm_base_url": "http://localhost:11434"
}
```
- 메인 UI 기본 모드는 `default_llm_*` 값을 자동 사용한다.
- `vectors=0`이면 사용자가 질의하기 전에 `Reindex`를 먼저 실행하도록 안내한다.

### GET `/collections`
- 목적: 컬렉션별 벡터 수/cap 사용률 조회
- 응답 예:
```json
{
  "default_collection_key": "all",
  "collections": [
    {
      "key": "all",
      "name": "w2_007_header_rag",
      "label": "전체 (기본)",
      "vectors": 37,
      "soft_cap": 30000,
      "hard_cap": 50000,
      "soft_usage_ratio": 0.0012,
      "hard_usage_ratio": 0.0007,
      "soft_exceeded": false,
      "hard_exceeded": false
    }
  ]
}
```

### POST `/reindex`
- 목적: `data/*.md` 기준 벡터 재생성
- 요청:
```json
{
  "reset": true,
  "collection": "all"
}
```
- 응답 예:
```json
{
  "docs": 5,
  "docs_total": 5,
  "chunks": 37,
  "vectors": 37,
  "persist_dir": "C:/.../chroma_db",
  "collection": "w2_007_header_rag",
  "collection_key": "all"
}
```

### POST `/query`
- 목적: 문서 기반 질의응답
- 요청:
```json
{
  "query": "각 국가별 대표적인 과학적 성과를 요약해줘",
  "collection": "all",
  "llm_provider": "ollama",
  "llm_model": "qwen3:4b",
  "llm_api_key": null,
  "llm_base_url": "http://localhost:11434"
}
```

### POST `/admin/auth`
- 목적: 관리자 인증코드 확인(초기 MVP)
- 요청:
```json
{
  "code": "admin1234"
}
```

### GET `/upload-requests`
- 목적: 업로드 요청 목록 조회(상태 필터 가능)
- 응답 예:
```json
{
  "auto_approve": false,
  "counts": {
    "pending": 2,
    "approved": 1,
    "rejected": 0
  },
  "requests": [
    {
      "id": "uuid",
      "status": "pending",
      "collection_key": "fr",
      "source_name": "new_doc.md",
      "usable": true
    }
  ]
}
```

### POST `/upload-requests`
- 목적: 일반 사용자 업로드 요청 생성
- 요청:
```json
{
  "source_name": "new_doc.md",
  "collection": "fr",
  "country": "france",
  "doc_type": "country",
  "content": "## 제목\n본문"
}
```
- 응답 예:
```json
{
  "auto_approve": false,
  "request": {
    "id": "uuid",
    "status": "pending",
    "usable": true
  }
}
```

### POST `/upload-requests/{id}/approve`
- 목적: 관리자 승인 및 인덱싱 반영
- 요청:
```json
{
  "code": "admin1234"
}
```

### POST `/upload-requests/{id}/reject`
- 목적: 관리자 반려
- 요청:
```json
{
  "code": "admin1234",
  "reason": "검증 기준 미달"
}
```
- 응답:
```json
{
  "ok": true
}
```
- 실패 응답 예:
```json
{
  "detail": "관리자 인증코드가 올바르지 않습니다."
}
```

### GET `/rag-docs`
- 목적: RAG 대상 문서 목록 조회
- 응답 예:
```json
{
  "docs": [
    {"name": "eu_summry.md", "size": 12829, "updated_at": 1766078655}
  ]
}
```

### GET `/rag-docs/{doc_name}`
- 목적: 특정 문서 원문 Markdown 조회
- 응답 예:
```json
{
  "name": "eu_summry.md",
  "content": "## ..."
}
```
- 응답 예:
```json
{
  "answer": "...",
  "provider": "ollama",
  "model": "qwen3:4b"
}
```

## 실행 기준
- 환경 파일 준비(권장):
```powershell
cd <repo>
copy .env.example .env
```
- `.env.example` 기본값은 로컬 우선(`ollama`, `qwen3:4b`)이다.
- 인덱스 생성:
```powershell
cd <repo>
python build_index.py --reset
```
- 서버 실행(권장):
```powershell
cd <repo>
.\run_doc_rag.bat
```
- 런처는 `.venv\Scripts\python.exe` 우선, 없으면 시스템 `python`을 사용한다.
- 런처는 `/health`가 200 응답이 될 때까지 최대 45초 대기한 뒤 `/intro`를 연다.
- 서버 실행(수동):
```powershell
cd <repo>
python app_api.py
```
- 첫 실행 또는 `vectors=0` 상태면 `/app` 왼쪽 메뉴의 `Reindex`를 먼저 실행한다.
- UI 접속:
- 인트로: `http://127.0.0.1:8000/intro`
- 메인: `http://127.0.0.1:8000/app`
- 관리자: `http://127.0.0.1:8000/admin`

## 설계 결정 기록
- 실습용 가변 파라미터를 줄이고 운영용 기본값은 `/health`를 통해 UI에 주입
- API 중심 구조 유지(FastAPI)로 UI/앱/확장 연동 재사용성 확보
- 문서 청킹 정책은 `##`, `###`, `####` 고정 + 분할 모드는 `char` 기본 유지
- LLM provider 다중 지원 유지(로컬 우선 + 외부 API 선택), 다만 기본 UX는 로컬 기본값 중심
- `trunk_rag`는 전처리된 md 소비자 역할에 집중
- 전처리는 외부 단계에서 수행하고, `trunk_rag`는 검증 게이트 중심으로 관리
- 쉬운 RAG 기본 경로를 위해 런처 readiness 대기와 고급 설정 기본 숨김 유지

## 제약 사항
- 추론 속도/품질은 로컬 하드웨어 성능에 크게 의존
- 현재는 단일 노드 운영 기준
- UI는 최소 운영 기능 중심(사이드바/차트/슬라이더 미사용)
- 데이터가 증가할수록 검색 지연과 노이즈 증가 가능

## 운영 경계(현행)
- 외부 전처리 단계:
  - 원본 소스 정제
  - 헤더/메타데이터 표준화
  - RAG 적합 md 산출
- `trunk_rag` 단계:
  - 산출 md 인덱싱/검색/질의
  - 등록 전 검증으로 사용 가능/불가 판정
  - 분야별 컬렉션 + 단순 라우팅

## 벡터스토어 정책
- 기본 컬렉션(`all`) + 분야별 컬렉션(`eu/fr/ge/it/uk`)을 운영
- 컬렉션당 cap은 `30,000 ~ 50,000 vectors`
- 벡터 수 증가 시 성능/품질 저하를 방지하기 위해 용량 정책 적용
- 상세는 `docs/VECTORSTORE_POLICY.md` 참조
- 컬렉션 라우팅 방식은 `docs/COLLECTION_ROUTING_POLICY.md` 참조

## 외부 제한사항 연계
- 외부 전처리 파이프라인 제약과 추후 내부 반영 항목은 `docs/FUTURE_EXTERNAL_CONSTRAINTS.md` 참조

## 다음 진행 방향
### 1순위
- 토큰 청킹 파라미터 재탐색
- `/query` 품질/지연 균형 재측정

### 2순위
- 운영 기본값 재확정
- 내용: `DOC_RAG_OLLAMA_NUM_PREDICT`, `DOC_RAG_MAX_CONTEXT_CHARS`, `DOC_RAG_QUERY_TIMEOUT_SECONDS`
- 내용: `README.md`, `SPEC.md`, 벤치 리포트 동기화

### 3순위
- 데스크톱 래핑(Electron/Tauri) PoC
- 내용: 로컬 서버 패키징 가능성 검토

### 4순위
- 문서 업로드/갱신 관리자 워크플로우 설계
- 내용: 운영 절차, 승인/반려 후속 처리, 갱신 정책 정의

## 완료 판정 기준
- `health/reindex/query` 정상 동작
- UI에서 질의/재인덱싱/문서목록 조회/문서보기 가능
- 공통 스타일 적용 유지
- provider 전환 시 치명적 오류 없음
