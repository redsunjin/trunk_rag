# doc_rag 다음 세션 계획 / 세션 핸드오버 (2026-03-17 기준)

기준 문서:
- `SPEC.md`
- `README.md`
- `TODO.md`
- `docs/GRAPH_RAG_QUESTION_SET.md`
- `docs/GRAPH_RAG_SIDECAR_CONTRACT.md`
- `docs/UPLOAD_ADMIN_WORKFLOW.md`
- `docs/reports/GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md`
- `docs/PREPROCESSING_RULES.md`
- `docs/VECTORSTORE_POLICY.md`
- `docs/COLLECTION_ROUTING_POLICY.md`
- `docs/reports/DESKTOP_WRAPPER_POC_REPORT_2026-03-17.md`
- `docs/reports/MULTI_COLLECTION_POC_REPORT_2026-02-26.md`
- `docs/reports/TOKEN_CHUNKING_POC_REPORT_2026-02-27.md`
- `docs/reports/QUERY_E2E_P95_REPORT_2026-02-27.md`
- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- `docs/NEXT_SESSION_CONTEXT_2026-02-28.md`
- `docs/WIP_SNAPSHOT_2026-02-28.md`

작성 목적:
- 세션 단절 이후에도 동일 기준으로 재진입할 수 있도록 상태를 단일 문서로 고정
- 완료/미완료 범위를 재정렬하고, 다음 작업 우선순위를 명확화

## 0. 2026-03-13 우선순위 재정렬

결론:
1. "쉬운 RAG 운영 경로" 정리는 2026-03-13에 완료됐다.
2. 성능/품질 게이트는 2026-03-15에 완료됐고, 운영 기본값은 `char` + 자동 다중 라우팅 기준으로 고정됐다.
3. 데스크톱 래핑 PoC는 2026-03-17에 Electron 기준으로 완료됐고, MVP에는 아직 넣지 않는다.
4. GraphRAG는 즉시 구현 대상이 아니라, 필요성 입증 후 사이드카 PoC로만 착수한다.

## 0.1 2026-03-17 제품화 후속 업데이트

결론:
1. 데스크톱 래핑은 기존 FastAPI + 웹 UI를 감싸는 Electron 셸 형태로 최소 실행 PoC가 가능했다.
2. `cargo` 부재와 현재 구조를 고려하면 이번 PoC 기준 구현 경로는 Tauri보다 Electron이 현실적이었다.
3. 업로드/갱신 관리자 워크플로우 설계도 완료됐고, 기준 문서는 `docs/UPLOAD_ADMIN_WORKFLOW.md`로 고정했다.
4. 관리자 워크플로우의 핵심 결정은 managed markdown 원본 + active 버전 기준으로 운영한다는 점이다.
5. Electron은 이제 시작 전 preflight로 repo/Python/backend import/기본 LLM 런타임을 먼저 점검한다.
6. 다만 데스크톱 PoC는 여전히 Python 런타임, 의존성 설치, LLM 준비 상태에 기대므로 MVP 기본 경로로 넣지 않는다.
7. 업로드/갱신 구현 1차가 반영돼 승인된 요청은 `chroma_db/managed_docs/` 기준으로 재구성된다.
8. `POST /upload-requests`는 `request_type/doc_key/change_summary`를 받고, `GET /rag-docs`와 `POST /reindex`는 seed + managed active 문서를 같은 기준으로 본다.
9. `DOC_RAG_AUTO_APPROVE`는 `create` 요청에만 적용되고 `update`는 항상 관리자 승인 경로를 탄다.
10. 데스크톱 패키징/배포 하드닝 재검토 결과, embedded Python/별도 설치 전략이 정해지기 전까지는 보류 유지로 판단했다.

## 0.2 2026-03-17 GraphRAG 게이트 업데이트

결론:
1. `docs/GRAPH_RAG_QUESTION_SET.md`에 관계형/다중 홉 질문 18개를 고정했다.
2. 질문은 `ops-baseline`과 `graph-candidate`로 분리했다.
3. `docs/reports/GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md`에 현재 Vector RAG 실패 사례와 구조적 한계를 정리했다.
4. `docs/GRAPH_RAG_SIDECAR_CONTRACT.md`에 최소 적재 파이프라인과 sidecar 계약을 정의했다.
5. GraphRAG 문서 준비 단계에서 남은 것은 실제 accuracy/latency 실측과 Go/No-Go 판단이다.

배경:
- 현재 프로젝트의 운영 모델은 `폐쇄망/로컬/경량 RAG 런타임`이다.
- 쉬운 RAG 1차 정리로 고급 설정 기본 숨김, 런처 readiness 대기, 업로드 최소 입력, 기본 문서/설정 동기화가 반영됐다.
- 동시에 `/query` p95는 `single_all` 기준 약 `39.2s`로 추가 구조 도입 전에 운영 기본값 재정리가 필요하다.

## 1. 현재 즉시 우선순위

### A. 쉬운 RAG 운영 게이트 (완료: 2026-03-13)
1. 실행/부트스트랩 단순화
- `run_doc_rag.bat` 경로 fallback 정리
- 브라우저 오픈 전 `/health` 준비 대기
- 실패 시 다음 행동 가이드 출력

2. 기본값 단일화
- 기본 provider/model/base_url 1세트 확정
- `.env.example`, UI 기본값, README 실행법 정렬

3. 사용자 화면 단순화
- 기본 모드에서 고급 LLM 설정 숨김 또는 접기
- 빈 인덱스/오프라인/모델 미실행 상태 안내 강화

4. 문서 등록 단순화
- 업로드 필수 입력 최소화
- 자동 추론 가능한 메타데이터 확대

완료 기준:
- 새 사용자 기준 "실행 -> 첫 질의 -> 업로드 요청"까지 별도 설명 없이 가능

검증:
- `.venv/bin/python -m pytest -q` -> `25 passed in 7.26s`

### B. 성능/품질 게이트 (완료: 2026-03-15)
1. 토큰 청킹 파라미터 재탐색
2. `/query` E2E 재측정
3. 단일/다중 컬렉션 기본 경로 재판정
4. 운영 권장 기본값과 리포트 갱신

완료 기준:
- 운영 기본값과 p95 기준을 문서로 고정

진행 메모 (2026-03-13):
- 토큰 청킹 스윕(`700/80`, `800/120`, `900/120`)은 실행 완료
- 다음 E2E 후보는 `token_800_120`, 보조 후보는 `token_700_80`
- `DOC_RAG_EMBEDDING_MODEL` override와 `scripts/runtime_preflight.py`가 추가돼 런타임 준비 상태를 먼저 판별할 수 있다.
- 초기 blocker였던 로컬 embedding model/base URL 문제는 local benchmark profile로 우회했다.
- `2026-03-14` local benchmark profile(`llama3.1:8b`, local embedding path, `DOC_RAG_EMBEDDING_DEVICE=cpu`)에서는 `/query` E2E 100% 성공으로 재개됐다.
- 같은 profile에서 `token_800_120` p95는 `char` 대비 `single_all -2.0%`, `single_fr -3.1%`, `dual_fr_ge -1.9%`였다.
- 다만 개선폭이 작고 공식 기본 스택이 아니므로 기본 청킹 모드는 당분간 `char` 유지로 둔다.
- `2026-03-15` 샘플 질의 품질 비교에서도 `char`와 `token_800_120` 차이는 확인되지 않았다.
- 자동 라우팅은 다중 국가 키워드 감지 시 최대 2개 컬렉션(`fr,ge` 등)을 함께 조회하도록 확정했다.
- `collection=all`은 fallback/명시 옵션으로 유지하고, 교차 국가 비교 질의의 기본 경로로는 두지 않는다.

검증:
- `.venv/bin/python -m pytest -q` -> `32 passed in 5.29s`

### C. 제품화 후속
1. 업로드/갱신 관리자 워크플로우 구현 2차

### D. GraphRAG 결정 게이트
1. 실제 accuracy/latency 실측
2. Go/No-Go 판단 후에만 GraphRAG PoC 착수

원칙:
- 기본 `/query`는 기존 Vector RAG 유지
- GraphRAG는 본체 직접 통합이 아니라 사이드카 우선
- AuraDB는 기본안이 아니며, 폐쇄망/로컬 요구가 유지되면 self-managed Neo4j 우선 검토

## 2. 2026-02-28 세션 업데이트 (이전 세션 반영)

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

## 3. 현재 상태 (핵심)

정량 스냅샷:
- `app_api.py`: 160 lines
- `web/index.html`: 193 lines
- `web/admin.html`: 70 lines
- `web/js/app_page.js`: 562 lines
- `web/js/admin_page.js`: 259 lines
- 전체 테스트: `34 passed`

판단:
- P3-Prep 게이트(`app_api.py <= 350`, inline script 외부화, 회귀 통과)는 충족됨.
- 쉬운 RAG 운영 게이트와 성능/품질 게이트는 완료됐고, 다음 우선순위는 제품화 후속 -> GraphRAG 결정 게이트 순이다.

## 4. 현재 남은 작업 범위 (핵심)

즉시 진행 대상 (다음 세션 1순위):
1. 업로드/갱신 관리자 워크플로우 구현 2차
2. GraphRAG actual PoC/실측

후속 대상 (P3):
1. GraphRAG 필요성 검증 및 사이드카 PoC 여부 결정
2. 업로드/갱신 관리자 워크플로우 구현 2차
3. 데스크톱 패키징은 embedded Python/설치 전략 결정 전까지 보류 유지

## 5. 다음 세션 우선순위 (실행 순서)

### A. 제품화 후속
1. 업로드/갱신 관리자 워크플로우 구현 2차

### B. GraphRAG 결정 게이트
1. Neo4j sidecar actual PoC/실측
2. AuraDB vs self-managed Neo4j 적용 조건 문서화

## 6. 세션 시작 체크리스트 (핸드오버용)

1. `git status --short`로 작업트리 확인
2. `.venv\Scripts\python.exe -m pytest -q`
3. `run_doc_rag.bat` 실행 후 `/intro`, `/app`, `/admin` 로딩 확인
4. `GET /health` 확인(벡터 수/auto_approve/pending/chunking_mode 확인)
5. `POST /reindex` 1회 실행(응답 내 `validation.summary_text` 확인)
6. `/query` 샘플 질의(단일 + 다중 컬렉션 자동 라우팅) 확인

추가 확인:
7. 기본 모드에서 LLM 세부 설정 없이 질의 가능한지 확인
8. 빈 인덱스/오류 상태에서 다음 행동 안내가 충분한지 확인

## 7. git worktree + agent 병렬 도입 계획 (권장)

결론:
- P3-Prep 분해가 완료되어, 다음 단계부터는 P3 기능 트랙 병렬화 가치가 높아짐.

도입 단계:
1. Stage A (파일럿 2트랙)
- Track-1(Core): 성능/품질 파라미터 실험 + 리포트
- Track-2(Product): 관리자 워크플로우 설계 + 데스크톱 패키징 판단

2. Stage B (확장 3트랙)
- Track-1: 데스크톱 패키징/배포 하드닝
- Track-2: 업로드/갱신 운영 정책/플로우
- Track-3: 회귀 QA/문서 동기화

## 8. 리스크 및 확인 포인트

1. 다중 컬렉션은 커버리지 이점이 있으나 p95 지연 상승 리스크 유지
2. 벤치 환경에 따라 LLM 응답 시간이 크게 변동될 수 있음
3. 서비스 분해 후 monkeypatch 경로가 바뀌었으므로 신규 테스트 작성 시 모듈 경로 준수 필요
4. 쉬운 RAG 개선 없이 기능만 추가하면 사용자 마찰이 누적될 수 있음
5. GraphRAG/AuraDB는 운영 모델(폐쇄망/로컬/경량)과 충돌 가능성이 큼
6. Electron PoC는 가능성을 확인했지만 설치형 제품으로 가려면 Python/모델 번들링 전략이 별도로 필요하며, 현재는 보류 상태다.
7. 업로드 관리자 워크플로우는 active 버전/manifest까지는 구현됐지만, diff 뷰/이력 조회/rollback UI는 아직 없다.

## 9. 다음 커밋 목표 (권장)

1. `feat(ux): simplify easy-rag bootstrap and defaults`
2. `perf(rag): remeasure query p95 and tune runtime defaults`
3. `docs(plan): reprioritize roadmap for easy-rag gate and graphrag decision`
4. `feat(upload): persist managed markdown and active-doc workflow`
5. `docs(desktop): record packaging hardening hold decision`
