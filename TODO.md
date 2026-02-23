# doc_rag TODO (Next Session Start)

목적:
- 다음 세션에서 바로 착수 가능한 작업 목록을 고정한다.
- `P0`를 먼저 완료하고 이후 `P1`로 넘어간다.

참조:
- `NEXT_SESSION_PLAN.md`
- `SPEC.md`
- `docs/PREPROCESSING_RULES.md`

## P0 (즉시 착수)

### 1) API/프론트 최소 회귀 테스트 추가
- [x] `tests/test_api_smoke.py` 생성
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

## Session Start Checklist

- [ ] `run_doc_rag.bat` 실행
- [ ] `/health` 확인
- [ ] `/reindex` 1회 실행
- [ ] `/query` 샘플 질의 2~3개 확인
- [x] P0의 1번부터 순차 수행

참고:
- 현재 저장소 `.venv`에는 `pytest`/`playwright`가 기본 포함되어 있지 않다.
- `requirements-dev.txt` 설치 후 테스트 실행/통과 여부를 최종 확인한다.

## P1 (다음 세션 핵심)

### 1) 전처리 가이드 제공(문서 템플릿 중심)
- [ ] `docs/PREPROCESSING_PROMPT_TEMPLATE.md` 생성
- [ ] `docs/PREPROCESSING_METADATA_SCHEMA.json` 생성
- [ ] 전처리 산출물 예시(`.md` + metadata) 1세트 정리

완료 기준:
- 외부 전처리 담당자가 동일 형식으로 산출물을 만들 수 있다.

### 2) 등록 시 검증 기능(usable 판정)
- [ ] 검증 스크립트/모듈 추가 (`scripts/validate_rag_doc.py` 또는 동등 기능)
- [ ] 검증 항목:
  - [ ] 헤더 구조(`##`, `###`, `####`)
  - [ ] 필수 메타(`source`, `country`, `doc_type`)
  - [ ] 최소 길이/빈 섹션
- [ ] 결과 출력:
  - [ ] `usable=true/false`
  - [ ] `reasons[]`

완료 기준:
- 인덱싱 전 문서의 RAG 사용 가능 여부를 자동 판정할 수 있다.

### 3) 벡터스토어 운영 정책 적용
- [ ] `docs/VECTORSTORE_POLICY.md` 기준 수치 확정
- [ ] 컬렉션당 cap `30k~50k vectors` 확정 (총량 기준 대략 `30M~50M tokens`)
- [ ] soft cap/hard cap 초과 시 운영 절차 문서화
- [ ] 분야별 컬렉션 분할 정책 반영
- [ ] 단순 라우팅 정책 반영(`사용자 선택 -> 키워드 매핑 -> fallback`)
- [ ] README/SPEC에 정책 링크 반영

완료 기준:
- 데이터 증가 시 성능/품질 저하 대응 기준이 명시되어 있다.
