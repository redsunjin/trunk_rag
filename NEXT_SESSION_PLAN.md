# doc_rag 진행 현황 및 다음 세션 우선순위

기준 문서:
- `SPEC.md`
- `README.md`

작성 목적:
- 오늘까지 구현된 항목과 미완료 항목을 구분
- 다음 세션에서 바로 시작할 수 있도록 우선순위 고정

## 1. 완료된 항목 (Done)

### A. 로컬 RAG 백엔드 기본 구조
- `app_api.py` FastAPI 서버 구성
- `POST /query`, `POST /reindex`, `GET /health` 구현
- 문서 목록/원문 조회 API 구현:
  - `GET /rag-docs`
  - `GET /rag-docs/{doc_name}`

### B. 문서/청킹/인덱싱 파이프라인
- `data/*.md` (5개 파일) 기반 로딩
- `##`, `###`, `####` 기준 헤더 청킹 + 문자 분할
- `BAAI/bge-m3` 임베딩 + Chroma 저장
- 인덱스 스크립트(`build_index.py`) 및 CLI 질의(`query_cli.py`) 구성

### C. UI 및 접근 경로
- 메인 UI: `web/index.html`
- 인트로 페이지: `web/intro.html`
- 스타일: `web/styles.css`
- 라우팅:
  - `/` -> `/intro` 리다이렉트
  - `/app` 메인 UI
- 문서 목록 + MD 뷰어 + 채팅 질의 화면 구성

### D. 실행 편의
- `run_doc_rag.bat` 추가
- 브라우저 수동 URL 입력 없이 `/intro` 진입 가능

## 2. 미완료/보완 필요 항목 (Not Done)

### A. 운영 안정성
- `/query` 실패 케이스별 표준 에러 응답 정교화
- LLM 타임아웃/재시도 정책 정리
- 서버 로깅 포맷 및 레벨 정책 정리

### B. 품질/검증
- API 자동 테스트(health/query/reindex/docs) 최소 세트 구축
- 프론트엔드 기능 테스트(문서 조회/질의/재인덱싱) 최소 검증 루틴 정리

### C. 전처리 워크플로우 분리
- 원본 md -> 정제 md 파이프라인 스크립트 별도화
- 문서 품질 규칙(헤더 구조, 메타데이터 규약) 문서화

### D. 배포/실행 형태
- 데스크톱 앱 래핑(Electron/Tauri) 여부 결정 전
- 현재는 로컬 서버 실행형 유지

## 3. 다음 세션 우선순위

### P0 (즉시)
1. API/프론트 최소 회귀 테스트 추가
2. `/query` 에러 처리 표준화
3. 문서 전처리 규칙 초안 확정

### P1 (다음)
1. 전처리 스크립트 분리(입력/출력 디렉터리 명확화)
2. 운영 로그 구조화(요청 ID, provider, model, latency)
3. README 실행 시나리오를 "인덱싱/서버/질의" 3단계로 재정리

### P2 (후속)
1. 데스크톱 앱 전환 PoC
2. 문서 업로드 관리자 UI 또는 관리 스크립트 설계

## 4. 다음 세션 시작 체크리스트

1. `run_doc_rag.bat`로 서버/인트로 기동 확인
2. `/health` 확인 후 `/reindex` 1회 실행
3. `/rag-docs` 문서 목록/`/rag-docs/{doc_name}` 원문 조회 확인
4. `/query` 기본 질의 2~3개로 응답 품질 확인
5. P0 작업부터 착수
