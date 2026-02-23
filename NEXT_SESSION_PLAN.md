# doc_rag 다음 세션 계획 (현행화)

기준 문서:
- `SPEC.md`
- `README.md`
- `docs/PREPROCESSING_RULES.md`
- `docs/VECTORSTORE_POLICY.md`
- `docs/COLLECTION_ROUTING_POLICY.md`
- `docs/FUTURE_EXTERNAL_CONSTRAINTS.md`

작성 목적:
- 현재 구현 완료 상태를 반영
- 합의된 운영모델(외부 전처리 + trunk_rag 검증 게이트)을 기준으로 다음 작업 우선순위를 고정

## 1. 현재 완료 상태 (Done)

### A. 로컬 RAG 런타임
- `app_api.py` FastAPI 서버 구성
- `POST /query`, `POST /reindex`, `GET /health` 구현
- 문서 목록/원문 조회 API 구현:
  - `GET /rag-docs`
  - `GET /rag-docs/{doc_name}`

### B. 안정성/품질 (P0 완료)
- `/query` 표준 에러 응답 적용:
  - `code`, `message`, `hint`, `request_id`, `detail`
- `/query` 타임아웃 정책(15초, 재시도 없음)
- `X-Request-ID` 응답 헤더 적용
- 테스트 구축:
  - API 스모크: `tests/test_api_smoke.py`
  - 프론트 E2E: `tests/e2e/test_web_flow_playwright.py`

### C. 전처리 정책 문서
- `docs/PREPROCESSING_RULES.md` 초안 작성

## 2. 운영 방향 확정 (중요)

1. `trunk_rag`는 "전처리된 md 소비자" 역할에 집중한다.
2. 원본 소스 정제/재작성은 외부 전처리 프로세스에서 수행한다.
3. `trunk_rag`는 다음 범위를 관리한다:
- 전처리 가이드 제공
- 데이터 등록 시 검증(사용 가능/불가 판정)
- 통과 문서만 벡터스토어 반영

## 3. 다음 세션 우선순위

### P1 (즉시)
1. 전처리 가이드 제공 산출물 추가
- 프롬프트 템플릿
- JSON 메타데이터 예시 포맷

2. 데이터 등록/인덱싱 전 검증 기능 추가
- 헤더 구조 검증(`##`, `###`, `####`)
- 메타 필수항목 검증(`source`, `country`, `doc_type`)
- RAG 사용 가능/불가(`usable=true/false`) 판정

3. 벡터스토어 운영 정책 문서화 및 경고 기준 확정
- soft cap / hard cap
- 초과 시 대응 절차(분리, 아카이브, 차단)

4. 분야별 컬렉션 + 단순 라우팅 설계 고정
- 컬렉션 분할 기준(도메인 단위)
- 라우팅 우선순위(사용자 선택 -> 키워드 매핑 -> 기본 fallback)
- 컬렉션당 cap(`30k~50k vectors`, 총량 기준 대략 `30M~50M tokens`) 연계

### P2 (다음)
1. 토큰 기준 청킹 전환 검증(가벼운 방식 유지 범위 내)
2. 검증 결과 리포트 출력 개선(JSON + 요약 텍스트)
3. 다중 컬렉션 조회(최대 2개 병렬) 옵션 검토

### P3 (후속)
1. 데스크톱 래핑(Electron/Tauri) PoC
2. 문서 업로드 관리자 워크플로우 설계

## 4. 다음 세션 시작 체크리스트

1. `run_doc_rag.bat`로 서버/인트로 기동 확인
2. `/health` 확인 후 `/reindex` 1회 실행
3. `/query` 샘플 질의 2~3개 응답 확인
4. 전처리 가이드/검증 기능(P1-1, P1-2)부터 착수
