# doc_rag TODO (Next Session Start)

목적:
- 다음 세션에서 바로 착수 가능한 작업 목록을 고정한다.
- `P0`를 먼저 완료하고 이후 `P1`로 넘어간다.

참조:
- `NEXT_SESSION_PLAN.md`
- `SPEC.md`

## P0 (즉시 착수)

### 1) API/프론트 최소 회귀 테스트 추가
- [ ] `tests/test_api_smoke.py` 생성
- [ ] 케이스:
  - [ ] `GET /health` == 200
  - [ ] `GET /rag-docs` == 200
  - [ ] `GET /rag-docs/{doc_name}` 성공/404 케이스
  - [ ] `POST /reindex` == 200
  - [ ] `POST /query` 성공/실패 케이스
- [ ] 실행 명령 정리 (`pytest` 기준)

완료 기준:
- 테스트가 로컬에서 통과하고, 실패 시 원인이 로그로 구분된다.

### 2) `/query` 에러 처리 표준화
- [ ] 에러 응답 포맷 통일:
  - [ ] `code`
  - [ ] `message`
  - [ ] `hint` (가능 시)
- [ ] 주요 실패 시나리오 반영:
  - [ ] 벡터스토어 비어 있음
  - [ ] LLM 연결 실패 (provider/base_url/api_key)
  - [ ] 타임아웃
  - [ ] 잘못된 요청 파라미터

완료 기준:
- 프론트에서 사용자에게 에러 원인을 명확히 안내할 수 있다.

### 3) 문서 전처리 규칙 초안 확정
- [ ] `docs/PREPROCESSING_RULES.md` 생성
- [ ] 규칙 정의:
  - [ ] 허용 헤더(`##`, `###`, `####`)
  - [ ] 제목/본문 최소 길이
  - [ ] 금지 패턴(빈 섹션, 중복 헤더 등)
  - [ ] 메타데이터 최소 항목(`source`, `country`, `doc_type`)
- [ ] 샘플 입력/출력 예시 1세트 작성

완료 기준:
- 누구나 동일 규칙으로 md 품질 점검 가능하다.

## P1 (P0 이후)

- [ ] 전처리 스크립트 분리 (`scripts/preprocess_md.py`)
- [ ] 운영 로그 구조화(요청 ID, provider, model, latency)
- [ ] README 실행 절차를 3단계(인덱싱/서버/질의)로 더 간결화

## P2 (후속)

- [ ] 데스크톱 래핑(Electron/Tauri) PoC
- [ ] 문서 업로드/갱신 관리자 워크플로우 설계

## Session Start Checklist

- [ ] `run_doc_rag.bat` 실행
- [ ] `/health` 확인
- [ ] `/reindex` 1회 실행
- [ ] `/query` 샘플 질의 2~3개 확인
- [ ] P0의 1번부터 순차 수행
