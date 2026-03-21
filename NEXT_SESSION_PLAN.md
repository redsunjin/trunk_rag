# doc_rag 다음 세션 계획 / 세션 핸드오버 (2026-03-20 기준)

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

## Session Loop Harness

- current_active_id: `LOOP-001`
- current_active_title: `배포형 웹 MVP 게이트`
- session_start_command: `./.venv/bin/python scripts/roadmap_harness.py status`
- default_regression_gate: `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider lmstudio --llm-model qwen3.5-4b-mlx-4bit --llm-base-url http://127.0.0.1:1337/v1`
- closeout_rule: `active` 항목은 검증 결과와 문서 반영, 커밋까지 끝난 뒤에만 `done`으로 본다.
- blocked_rule: blocker와 재개 조건 없이 `blocked` 상태로 이동하지 않는다.
- promotion_rule: 현재 `active`가 `done`이 되면 첫 번째 `pending` 항목을 즉시 다음 `active`로 승격한다.

## 0. 2026-03-13 우선순위 재정렬

결론:
1. "쉬운 RAG 운영 경로" 정리는 2026-03-13에 완료됐다.
2. 성능/품질 게이트는 2026-03-15에 완료됐고, 운영 기본값은 `char` + 자동 다중 라우팅 기준으로 고정됐다.
3. 데스크톱 래핑 PoC는 2026-03-17에 Electron 기준으로 완료됐고, MVP에는 아직 넣지 않는다.
4. GraphRAG는 2026-03-20 기준 잠정 중단 상태로 두고, 기존 문서/PoC는 아카이브로만 유지한다.
5. 2026-03-20 이후 active 루프는 "내부 운영형 MVP 유지"가 아니라 "배포형 웹 MVP 게이트"를 닫는 방향으로 본다.

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
11. 2026-03-20 기준 Electron 경로는 정식 패키징이 아니라 선택형 앱 런처로 유지한다.

## 0.2 2026-03-17 GraphRAG 게이트 업데이트 (아카이브)

결론:
1. `docs/GRAPH_RAG_QUESTION_SET.md`에 관계형/다중 홉 질문 18개를 고정했다.
2. 질문은 `ops-baseline`과 `graph-candidate`로 분리했다.
3. `docs/reports/GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md`에 현재 Vector RAG 실패 사례와 구조적 한계를 정리했다.
4. `docs/GRAPH_RAG_SIDECAR_CONTRACT.md`에 최소 적재 파이프라인과 sidecar 계약을 정의했다.
5. `services/graphrag_poc_service.py`와 `scripts/benchmark_graphrag_sidecar.py`로 graph snapshot 기반 retrieval PoC를 추가했다.
6. `docs/reports/GRAPH_RAG_ACTUAL_POC_REPORT_2026-03-17.md` 기준 6개 graph-candidate 질문의 1차 실측 결과는 `avg_latency_ms=0.068`, `avg_expected_entity_hit_ratio=0.9444`였다.
7. `evals/answer_level_eval_fixtures.jsonl`와 `scripts/eval_query_quality.py`로 answer-level 자동 채점 하네스를 추가했다.
8. `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md` 기준 Vector RAG 1차 baseline 실측은 `pass_rate=0.3333`, `avg_weighted_score=0.593`, `p95_latency_ms=14277.843`이었다.
9. 같은 실측에서 `GQ-03`은 `VECTORSTORE_EMPTY`, `GQ-05`는 `LLM_TIMEOUT`으로 실패했다.
10. `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md` 기준 graph snapshot backend의 `graph-candidate` answer-level 비교는 `2/3 pass`, `avg_weighted_score=0.8444`, `p95_latency_ms=0.074`였다.
11. `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md` 결론은 "MVP 통합 No-Go"였다.
12. 2026-03-20 기준 GraphRAG 관련 신규 구현/평가를 잠정 중단하고, 기존 문서/리포트/PoC만 아카이브로 유지한다.
13. `2026-03-19` 기준 `/reindex`와 `build_index.py --reset` 기본 경로는 `all/eu/fr/ge/it/uk` 전체를 함께 재생성한다.
14. 같은 재인덱싱 후 로컬 벡터 수는 `all=37`, `eu=9`, `fr=7`, `ge=7`, `it=7`, `uk=7`로 확인됐다.
15. `DOC_RAG_MAX_CONTEXT_CHARS` 미설정 시 기본 `1500`자를 적용하고, 컨텍스트는 그 예산 안에서 잘라 구성한다.
16. `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_OPS_RELIABILITY.md` 기준 `ops-baseline` 3건은 모두 `200` 응답이며 `VECTORSTORE_EMPTY`/`LLM_TIMEOUT` blocker는 해소됐다.
17. `2026-03-19`에는 `services/query_service.py`에 질문 유형별 answer 후처리(`역할/비교/상징`)를 추가해 표현 정합성을 보정했다.
18. `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` 기준 최신 `ops-baseline`은 `3/3 pass`, `avg_weighted_score=0.9645`, `p95_latency_ms=8724.427`이다.
19. 현재 기본 경로의 남은 과제는 blocker 복구가 아니라 이 기준을 회귀 게이트로 유지하는 것이다.
20. `scripts/check_ops_baseline_gate.py`로 `all-routes` 벡터 상태와 `ops-baseline` `3/3 pass`를 한 번에 점검할 수 있다.

배경:
- 현재 프로젝트의 운영 모델은 `폐쇄망/로컬/경량 RAG 런타임`이다.
- 쉬운 RAG 1차 정리로 고급 설정 기본 숨김, 런처 readiness 대기, 업로드 최소 입력, 기본 문서/설정 동기화가 반영됐다.
- 동시에 `/query` p95는 `single_all` 기준 약 `39.2s`로 추가 구조 도입 전에 운영 기본값 재정리가 필요하다.

## 1. 현재 즉시 우선순위

### A. 배포형 웹 MVP 게이트 (현재 active)
1. 단일 부트스트랩/설치 경로 고정
- 웹 UI 기준 기본 설치/실행 경로를 1개로 고정
- 운영자가 따라야 할 준비 항목(Python, requirements, 임베딩, LLM)을 문서/스크립트 기준으로 일치시킴

2. 첫 실행 성공 경로 강화
- `run_doc_rag.bat`와 `/intro`를 기준으로 첫 실행에서 다음 행동이 분명해야 함
- 실패 시 복구 경로가 사용자 관점 문구로 정리돼야 함

3. 릴리즈 운영 체크리스트 고정
- `ops-baseline` 회귀 게이트
- all-routes 인덱싱 상태 확인
- 운영 문서/핸드오버 문서 동기화

완료 기준:
- 웹 UI 기본 경로만으로 설치, 실행, 첫 질의, 업로드 요청, 관리자 확인까지 배포 가이드 기준으로 재진입 가능
- 릴리즈 전 검증 명령과 장애 복구 안내가 문서/스크립트로 고정됨

검증:
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider lmstudio --llm-model qwen3.5-4b-mlx-4bit --llm-base-url http://127.0.0.1:1337/v1`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

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

### C. MVP 기본 경로 품질 보정 (완료: 2026-03-19)
1. `ops-baseline` answer completeness 보정(`역할/비교/상징` 표현 정합성 개선) 완료
2. `QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` 기준 `3/3 pass` 확인
3. `build_index.py --reset` / `/reindex`의 all-routes 동작을 운영 가이드에 고정

### D. 제품화 후속
1. 업로드/갱신 관리자 워크플로우 구현 2차 완료 상태 유지
2. 데스크톱 경로는 선택형 앱 런처로 유지하고, 패키징은 재착수 조건이 충족되기 전까지 보류 유지

원칙:
- 기본 `/query`는 기존 Vector RAG 유지
- GraphRAG는 잠정 중단 상태이며 신규 구현/평가를 진행하지 않음
- AuraDB는 현재 검토 대상이 아니며, 관련 판단은 GraphRAG 재개 시점에 다시 본다

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
- 전체 테스트: `56 passed`

판단:
- P3-Prep 게이트(`app_api.py <= 350`, inline script 외부화, 회귀 통과)는 충족됨.
- 쉬운 RAG 운영 게이트와 성능/품질 게이트는 완료됐고, answer-level eval harness까지 준비됐다.
- 업로드/갱신 관리자 워크플로우 2차는 완료됐고, GraphRAG 트랙은 "MVP 통합 No-Go" 판단 이후 잠정 중단 상태로 정리됐다.
- Vector baseline 신뢰성 복구와 answer completeness 보정은 완료됐고, 이후에는 `ops-baseline`을 기본 경로 회귀 게이트로 유지한다.

## 4. 현재 남은 작업 범위 (핵심)

즉시 진행 대상 (다음 세션 1순위):
1. 배포형 웹 MVP 기준 단일 설치/실행 경로 고정
2. 첫 실행 성공 경로와 복구 가이드 강화
3. 릴리즈 체크리스트를 `ops-baseline` + all-routes 게이트와 연결

진행 메모 (2026-03-20):
- `run_doc_rag.bat`는 이제 웹 MVP 기준 단일 부트스트랩/실행 엔트리포인트다.
- `scripts/bootstrap_web_release.py`로 `.env`, `.venv`, runtime requirements 준비를 자동화했다.
- 단일 설치/실행 경로 고정용 타깃 검증(`tests/test_runtime_preflight.py`, `tests/api/test_system_api.py`)은 통과했다.
- `/health`와 `/query` 복구 안내가 `run_doc_rag.bat`와 `/intro` 기준으로 연결되도록 정리했다.
- `docs/RELEASE_WEB_MVP_CHECKLIST.md`를 추가해 릴리즈/운영 체크리스트를 단일 문서로 고정했다.
- 문서/타깃 테스트 기준 `LOOP-004`까지는 완료됐다.
- `2026-03-21` 실측에서는 앱 기동 후 첫 release gate가 `VECTORSTORE_EMBEDDING_MISMATCH(409)`로 막혔고, all-routes 인덱스를 현재 임베딩 차원으로 다시 생성해야 함을 확인했다.
- 같은 날짜 `env HF_HUB_OFFLINE=1 ./.venv/bin/python build_index.py --reset` 뒤 `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434 --json` 결과는 `pass_rate=1.0`, `avg_weighted_score=0.9645`, `p95_latency_ms=13501.527`로 통과했다.
- 오프라인/폐쇄망 환경에서는 HuggingFace cache가 이미 있으면 `HF_HUB_OFFLINE=1`을 붙인 재인덱싱 경로를 우선 복구안으로 사용한다.
- `2026-03-21`부터 본 로컬 PC 기본 경로는 `LM Studio` 기준으로 정렬하며, 회귀 게이트 기본 명령은 `--llm-provider lmstudio --llm-model qwen3.5-4b-mlx-4bit --llm-base-url http://127.0.0.1:1337/v1`를 사용한다.
- `LM Studio` live gate는 `qwen3.5-4b-mlx-4bit`가 실제로 로드되어 있을 때만 통과 여부를 판단할 수 있다.
- 같은 날짜 `LM Studio` `qwen3.5-4b-mlx-4bit` + `http://127.0.0.1:1337/v1` live gate 실측에서는 runtime/all-routes는 모두 ready였지만 `ops-baseline` 3건이 전부 `LLM_TIMEOUT`으로 실패했다.
- `DOC_RAG_QUERY_TIMEOUT_SECONDS=30`으로 재실험해도 `pass_rate=0.0`, `p95_latency_ms=35668.911`로 여전히 timeout이어서, 현재 blocker는 연결이 아니라 LM Studio 기본 모델의 응답 지연이다.
- `2026-03-21`에는 `scripts/check_ops_baseline_gate.py`가 `runtime_preflight` 선행 + `APP_HEALTH_UNREACHABLE` / `COLLECTIONS_CHECK_FAILED` / `OPS_EVAL_FAILED` 진단 출력을 하도록 보강됐다.
- 같은 날짜 로컬 게이트 실행에서는 서버 미기동 상태가 `APP_HEALTH_UNREACHABLE`로 즉시 드러났고, `/query`는 임베딩 차원 불일치를 `VECTORSTORE_EMBEDDING_MISMATCH(409)`로 안내하도록 정리됐다.
- 회귀 검증은 `./.venv/bin/python -m pytest -q` -> `69 passed in 7.65s`, `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`까지 확인했다.

후속 대상 (P3):
1. GraphRAG 관련 문서/PoC는 잠정 중단 상태의 아카이브로만 유지
2. 데스크톱 패키징은 embedded Python/설치 전략 결정 전까지 보류 유지

## 5. 다음 세션 우선순위 (실행 순서)

### A. MVP 기본 경로 품질 유지
1. 릴리즈 전 기본 설치/실행/복구 경로를 문서와 스크립트 기준으로 1개로 고정
2. `ops-baseline`의 `3/3 pass` 상태를 릴리즈 회귀 게이트로 유지
3. `scripts/check_ops_baseline_gate.py` 기준으로 `build_index.py --reset` / `/reindex`의 all-routes 동작과 eval 결과를 함께 확인

### B. 보류/유지 항목
1. GraphRAG는 `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md` 기준으로 잠정 중단 상태를 유지하고 신규 구현/평가는 진행하지 않음
2. 데스크톱 패키징은 `embedded Python` vs `별도 설치` 결정 전까지 재착수하지 않음

## 6. 세션 시작 체크리스트 (핸드오버용)

1. `git status --short`로 작업트리 확인
2. `.venv\Scripts\python.exe -m pytest -q`
3. `run_doc_rag.bat` 실행 후 `/intro`, `/app`, `/admin` 로딩 확인
4. `GET /health` 확인(벡터 수/auto_approve/pending/chunking_mode 확인)
5. `POST /reindex` 1회 실행(응답 내 `validation.summary_text` 확인)
6. `/query` 샘플 질의(단일 + 다중 컬렉션 자동 라우팅) 확인
7. `./.venv\Scripts\python.exe scripts\check_ops_baseline_gate.py --llm-provider lmstudio --llm-model qwen3.5-4b-mlx-4bit --llm-base-url http://127.0.0.1:1337/v1` 1회 실행

추가 확인:
8. 기본 모드에서 LLM 세부 설정 없이 질의 가능한지 확인
9. 빈 인덱스/오류 상태에서 다음 행동 안내가 충분한지 확인

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
5. GraphRAG/AuraDB는 운영 모델(폐쇄망/로컬/경량)과 충돌 가능성이 커서 현재는 잠정 중단 상태를 유지한다.
6. Electron PoC는 가능성을 확인했지만 설치형 제품으로 가려면 Python/모델 번들링 전략이 별도로 필요하며, 현재는 보류 상태다.
7. 업로드 관리자 워크플로우는 active 버전/manifest까지는 구현됐지만, diff 뷰/이력 조회/rollback UI는 아직 없다.
8. GraphRAG 실험 결과는 판단 이력으로는 남아 있지만, 현재 운영 의사결정 기준은 `ops-baseline` 회귀 게이트 유지다.
9. 현재 answer-level eval fixture는 대표 질문 6개만 포함하고, `uk` 컬렉션 비어 있음/다중 컬렉션 timeout 같은 운영 이슈가 그대로 드러난다.

## 9. 다음 커밋 목표 (권장)

1. `feat(ux): simplify easy-rag bootstrap and defaults`
2. `perf(rag): remeasure query p95 and tune runtime defaults`
3. `docs(plan): reprioritize roadmap for easy-rag gate and graphrag decision`
4. `feat(upload): persist managed markdown and active-doc workflow`
5. `docs(desktop): record packaging hardening hold decision`
6. `docs(plan): archive graphrag track as paused`
7. `feat(eval): add answer-level query quality harness`
