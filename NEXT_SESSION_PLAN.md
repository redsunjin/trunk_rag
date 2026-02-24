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
- 다음 세션에서 바로 구현 가능한 기능 단위로 작업을 재배열

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
4. 사용자/관리자 UX를 분리한다:
- 사용자: 기존 채팅 UI 유지 + 컬렉션 선택 기능만 추가
- 관리자: 업로드 요청 검증/승인 + 컬렉션 용량 관리
5. 업로드 권한 정책:
- 일반 사용자는 md 업로드 "요청" 가능
- 관리자는 요청 승인 후 인덱싱 반영
- 개인 운영(관리자=사용자) 모드에서는 `auto-approve` 옵션 허용

## 3. 다음 세션 우선순위

### P1 (즉시)
1. 전처리 가이드 제공 산출물 추가
- 프롬프트 템플릿
- JSON 메타데이터 예시 포맷

2. 컬렉션 라우팅 기반 API 확장
- `GET /collections` (벡터수/cap 사용률)
- `/query`에 `collection` 파라미터 추가(기본값 유지)
- 컬렉션별 cap(`30k~50k`) 사전 검증

3. 사용자/관리자 진입 분리(인트로)
- `/intro`에서 `사용자`/`관리자` 분기
- 관리자 진입은 인증코드 기반(초기 MVP)

4. 데이터 등록/인덱싱 전 검증 기능 추가
- 헤더 구조 검증(`##`, `###`, `####`)
- 메타 필수항목 검증(`source`, `country`, `doc_type`)
- RAG 사용 가능/불가(`usable=true/false`) 판정

5. 업로드 요청-승인 워크플로우 추가
- 일반 사용자: 업로드 요청 생성(`pending`)
- 관리자: 승인/반려 처리(`approved/rejected`)
- 승인 시에만 벡터스토어 반영

6. 벡터스토어 운영 정책 적용
- soft cap / hard cap
- 초과 시 대응 절차(분리, 아카이브, 차단)
- 컬렉션당 cap(`30k~50k vectors`, 총량 기준 대략 `30M~50M tokens`) 연계

### P2 (다음)
1. 관리자 UI(`/admin`) 고도화
- 컬렉션별 여유율 시각화
- 요청 이력/반려 사유 검색
2. 토큰 기준 청킹 전환 검증(가벼운 방식 유지 범위 내)
3. 검증 결과 리포트 출력 개선(JSON + 요약 텍스트)
4. 다중 컬렉션 조회(최대 2개 병렬) 옵션 검토

### P3 (후속)
1. 데스크톱 래핑(Electron/Tauri) PoC
2. 문서 업로드 관리자 워크플로우 설계

## 4. 다음 세션 시작 체크리스트

1. `run_doc_rag.bat`로 서버/인트로 기동 확인
2. `/health` 확인 후 `/reindex` 1회 실행
3. `/query` 샘플 질의 2~3개 응답 확인
4. 인트로 사용자/관리자 분기 및 컬렉션 선택 UI부터 착수
5. 업로드 요청/승인 흐름(P1-5)까지 MVP 완료

## 5. 세션 업데이트 (2026-02-24)

완료:
- 전처리 가이드 산출물 추가
  - `docs/PREPROCESSING_PROMPT_TEMPLATE.md`
  - `docs/PREPROCESSING_METADATA_SCHEMA.json`
  - `docs/examples/preprocessed_sample.md`
  - `docs/examples/preprocessed_sample.metadata.json`
- 컬렉션 API/라우팅 1차 반영
  - `GET /collections`
  - `/query`의 `collection` 파라미터 + 키워드 라우팅 + fallback
  - `/reindex`의 컬렉션 선택 + hard cap 사전 검증
- 사용자/관리자 진입 분리 1차 반영
  - `/intro` 사용자/관리자 분기
  - `POST /admin/auth` 인증코드 체크
  - `/admin` 상태 페이지 추가
- 업로드 요청/승인 워크플로우 1차 반영
  - `pending/approved/rejected` 상태모델
  - 사용자 업로드 요청 API/UI
  - 관리자 승인/반려 API/UI
  - `DOC_RAG_AUTO_APPROVE` 옵션 반영
- 등록 전 검증 기능 1차 반영
  - `scripts/validate_rag_doc.py`
  - `usable/reasons/warnings` 산출
  - `/reindex` 응답에 검증 요약 포함

잔여:
- 관리자 반려 사유/이력 검색 UI 고도화
- 다중 컬렉션 조회(최대 2개 병렬) 옵션 검토

## 6. Graph/Lang 도입 검토 (2026-02-24)

- 검토 문서: `Graph_Lang도입검토.md` (원문: `통합graph_lang설명.md`)
- 결론: 본체 직접 통합보다 **사이드카 방식** 권고
  - 본체(`doc_rag`)는 경량 질의 경로를 유지
  - Graph/Lang은 고급 오케스트레이션을 별도 프로세스로 분리
- 이유:
  - 현 프로젝트 목표(로컬/경량/단순 운영)와 충돌 최소화
  - 장애 격리 및 롤백/실험 용이성 확보
  - p95 지연 변동성 관리에 유리
