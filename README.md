[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


# Trunk RAG (Local Server)

폐쇄망/로컬 환경에서 사용하는 경량 RAG 서버이며, 현재 목표는 "배포 가능한 웹 MVP" 기준으로 웹 UI 기본 경로를 닫는 것입니다.

현재 버전 기준은 `V1 = RAG product`다. 다음 단계는 `V2 = Agent-enabled RAG`, 장기 목표는 `V3 = Agent system`이며, 버전 경계와 후속 아키텍처 기준은 `VERSION_ROADMAP.md`를 따른다.

- 문서: 전처리 완료된 `data/*.md` 입력
- 청킹: `##`, `###`, `####` 헤더 기반 + 문자 분할(기본), 토큰 분할(옵션)
- 벡터스토어: Chroma (로컬 폴더)
- LLM: `openai` / `ollama` / `lmstudio` / `groq` 선택(기본 예시: `ollama` + `llama3.1:8b`)
- 인터페이스: FastAPI + 브라우저(`http://127.0.0.1:8000`)
- 업로드 워크플로우: 사용자 요청(`pending`) -> 관리자 승인/반려

## Operating Model (현행화)

`trunk_rag`는 "가벼운 RAG 런타임" 역할에 집중합니다.

- 현재 제품 경계: `V1`
- 현재 범위 밖: `tool registry`, `skill registry`, `middleware chain`, `agent runtime`, `MCP` 기반 외부 tool orchestration

1. 외부 전처리 단계(별도 프로세스, 클라우드 LLM 포함 가능)
- 원본 소스를 정제해 RAG 정책에 맞는 Markdown으로 변환
- 메타데이터(`source`, `country`, `doc_type`)를 채운 산출물 생성

2. `trunk_rag` 단계(현재 + 다음 우선순위)
- 현재: 정제된 md를 인덱싱/검색/질의
- 현재: 데이터 등록 시 검증(사용 가능/불가 판정) 적용
- 현재: 분야별 컬렉션 + 단순 라우팅 적용
- 현재: 승인된 업로드는 `chroma_db/managed_docs/`의 active markdown 원본 기준으로 유지
- 현재: answer-level eval fixture + `/query` 품질 평가 하네스 추가
- 현재: Vector RAG answer-level baseline 1차 실측 완료(`pass_rate=0.3333`, `p95=14277.843ms`)
- 현재: 업로드 관리자 Slice 2 완료(`pending` 기본 필터, update 강조, active 문서 미리보기, reject reason code/decision_note)
- 아카이브: graph snapshot backend의 `graph-candidate` answer-level 비교는 `2/3 pass`, `avg_weighted_score=0.8444`
- 현재 판단: GraphRAG 트랙은 잠정 중단 상태이며, 기존 문서/PoC는 참고용 아카이브로만 유지한다
- 현재: `/reindex`와 `build_index.py --reset` 기본 경로는 `all/eu/fr/ge/it/uk`를 함께 재생성한다
- 현재: `ops-baseline` 재측정 기준 `VECTORSTORE_EMPTY`/`LLM_TIMEOUT` blocker는 해소됐다
- 현재: `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` 기준 `ops-baseline`은 `3/3 pass`, `avg_weighted_score=0.9645`다
- 현재: `/query`는 runtime profile 기반 query budget(`single/multi`, `verified/experimental/not_recommended`)을 내부 정책으로 적용한다
- 현재: `/health`는 `runtime_query_budget_*`, `embedding_fingerprint_*` 상태를 노출해 경량 경로와 인덱스 호환 상태를 먼저 보여 준다
- 현재: reindex 시 컬렉션별 embedding fingerprint를 저장하고, `/query`는 mismatch를 invoke 전에 먼저 차단한다
- 다음 우선순위(P2/P3): 배포형 웹 MVP 기준 설치/실행/복구 경로를 고정하고, 기본 `/query` 회귀 게이트를 릴리즈 체크리스트로 유지

비목표(현재 단계):
- 원본 수집/크롤링
- 대규모 자동 재작성 파이프라인
- 무거운 rerank/multi-vector 파이프라인 기본 탑재
- GraphRAG 통합/sidecar 운영

## Files

- `app_api.py`: FastAPI 앱 엔트리포인트/조립 계층
- `api/routes_*.py`: API/UI 라우트 모듈
- `services/*.py`: 질의/인덱싱/업로드 서비스 모듈
- `core/*.py`: 설정/에러/HTTP 유틸
- `build_index.py`: 초기 인덱스 생성 스크립트
- `common.py`: 공통 유틸리티
- `web/index.html`: 간단 웹 UI
- `web/intro.html`: 인트로/상태 확인 페이지
- `web/admin.html`: 관리자 상태 페이지(MVP)
- `web/js/*.js`: 프론트엔드 로직 모듈
- `web/styles.css`: 공통 스타일
- `scripts/validate_rag_doc.py`: 등록 전 문서 검증 스크립트
- `scripts/benchmark_multi_collection.py`: 단일/다중 컬렉션 검색 비교 벤치
- `scripts/benchmark_token_chunking.py`: char/token 청킹 비교 벤치 스크립트
- `scripts/benchmark_query_e2e.py`: `/query` E2E p95 벤치 스크립트
- `scripts/benchmark_graphrag_sidecar.py`: GraphRAG sidecar retrieval PoC/실측 스크립트
- `scripts/eval_query_quality.py`: answer-level `/query` 품질 평가 스크립트
- `scripts/check_ops_baseline_gate.py`: all-routes 벡터 상태와 `ops-baseline` 회귀 게이트를 한 번에 점검하는 스크립트
- `scripts/bootstrap_web_release.py`: 웹 MVP 기본 경로용 `.env`/`.venv`/requirements 부트스트랩 스크립트
- `scripts/roadmap_harness.py`: `TODO.md`/`NEXT_SESSION_PLAN.md`의 루프 상태와 active 항목을 점검하는 스크립트
- `scripts/runtime_preflight.py`: P1 벤치 전 런타임 준비 상태 점검
- `scripts/diagnose_ollama_runtime.py`: Ollama 직접 호출 기준 `eval_tokens_per_second`/wall time 진단 스크립트
- `chroma_db/embedding_fingerprints.json`: 컬렉션별 임베딩 fingerprint 메타데이터
- `run_doc_rag.bat`: 배포형 웹 MVP 기준 단일 부트스트랩/실행 엔트리포인트
- `run_doc_rag_desktop.bat`: Windows에서 Electron 데스크톱 런처 실행
- `stop_doc_rag.bat`: 실행 중인 로컬 서버 종료
- `desktop/electron/*`: 기존 웹 UI를 감싸는 실험용 Electron 데스크톱 래퍼 PoC
- `desktop/electron/README.md`: 데스크톱 런처 사용 방법과 한계
- `AGENTS.md`: 에이전트용 상시 작업 정책
- `WORKFLOW.md`: 사람/에이전트 공통 작업 순서
- `VERSION_ROADMAP.md`: `V1/V2/V3` 버전 경계와 `V2` agent architecture 기준
- `requirements.txt`: 런타임 의존성
- `requirements-dev.txt`: 테스트/브라우저 의존성
- `.env.example`: 환경변수 템플릿
- `docs/PREPROCESSING_RULES.md`: 전처리 규칙 초안
- `docs/PREPROCESSING_PROMPT_TEMPLATE.md`: 전처리 프롬프트 템플릿
- `docs/PREPROCESSING_METADATA_SCHEMA.json`: 전처리 메타데이터 스키마
- `docs/UPLOAD_ADMIN_WORKFLOW.md`: 업로드/갱신 관리자 워크플로우 설계 기준
- `docs/HARNESS_MASTER_GUIDE.md`: 하네스 설계 원칙, 워크북 템플릿, 현재 구조 심사 기준
- `docs/HARNESS_EVOLUTION_PLAN.md`: 버전별 하네스 모드와 세션 메타데이터 계약
- `docs/RELEASE_WEB_MVP_CHECKLIST.md`: 배포형 웹 MVP 릴리즈 체크리스트
- `docs/GRAPH_RAG_QUESTION_SET.md`: GraphRAG 판단용 관계형 질문셋
- `evals/answer_level_eval_fixtures.jsonl`: answer-level 평가 fixture
- `docs/GRAPH_RAG_SIDECAR_CONTRACT.md`: GraphRAG sidecar 계약과 최소 적재 파이프라인
- `docs/reports/GRAPH_RAG_ACTUAL_POC_REPORT_2026-03-17.md`: GraphRAG retrieval PoC 1차 실측 결과
- `docs/reports/GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md`: 현재 Vector RAG 실패 사례와 Graph 후보 범위
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`: Vector RAG 1차 answer-level baseline 실측 결과
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md`: 최신 ops-baseline answer completeness 보정 결과
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md`: graph snapshot backend answer-level 비교 결과
- `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md`: GraphRAG Go/No-Go 판단 문서
- `docs/VECTORSTORE_POLICY.md`: 벡터스토어 운영/용량 정책
- `docs/COLLECTION_ROUTING_POLICY.md`: 분야별 컬렉션/라우팅 정책
- `docs/FUTURE_EXTERNAL_CONSTRAINTS.md`: 외부 제한사항 중 추후 적용 항목
- `docs/reports/DESKTOP_WRAPPER_POC_REPORT_2026-03-17.md`: 데스크톱 래핑 PoC 결과 및 MVP 반영 판단
- `docs/reports/DESKTOP_PACKAGING_HARDENING_REVIEW_2026-03-17.md`: 데스크톱 패키징/배포 하드닝 재검토 결과

## Release Web MVP Path

배포형 웹 MVP 기준 권장 경로는 `run_doc_rag.bat` 하나입니다. 첫 실행 시 이 스크립트가 `.env`, `.venv`, `requirements.txt` 설치를 가능한 범위에서 자동으로 준비한 뒤 서버와 브라우저를 엽니다.

1. Python 3 설치 확인:
```powershell
cd <repo>
python --version
```
2. Windows 기본 실행:
```powershell
cd <repo>
.\run_doc_rag.bat
```
   - `.venv`가 없으면 자동 생성합니다.
   - `.env`가 없으면 `.env.example`을 복사합니다.
   - 런타임 패키지가 없으면 `requirements.txt` 설치를 시도합니다.
   - `/health`가 준비될 때까지 최대 45초 대기한 뒤 `http://127.0.0.1:8000/intro`를 엽니다.
   - 완전 오프라인 환경에서는 임베딩 모델 `BAAI/bge-m3`를 사전에 로컬 캐시에 준비하거나 `DOC_RAG_EMBEDDING_MODEL`로 로컬 경로를 지정해야 합니다.
3. 첫 실행이거나 상태 메시지에 `vectors=0`이 보이면 먼저 인덱싱:
   - 브라우저 왼쪽 메뉴에서 `Reindex`를 실행하거나
```powershell
cd <repo>
.venv\Scripts\python.exe build_index.py --reset
```
   - 기본 `Reindex`와 `build_index.py --reset`은 이제 `all/eu/fr/ge/it/uk` 전체 라우트 컬렉션을 함께 갱신합니다.
4. 선택형 데스크톱 런처를 쓰려면:
```powershell
cd <repo>\desktop\electron
npm install
cd <repo>
.\run_doc_rag_desktop.bat
```
   - 이 경로는 브라우저 대신 Electron 창으로 `/intro`를 여는 선택형 런처입니다.
   - 정식 설치형 앱은 아니며, Python/LLM/임베딩 준비 상태는 여전히 필요합니다.
5. 수동 실행이 필요하면:
```powershell
cd <repo>
.venv\Scripts\python.exe app_api.py
```
6. 브라우저에서 `http://127.0.0.1:8000/intro`가 열리고, `사용자 모드 시작` 버튼으로 `/app` 진입.
   - 관리자 모드는 인증 코드 입력 후 `/admin` 진입
7. Windows 배치 실행 종료:
```powershell
cd <repo>
.\stop_doc_rag.bat
```

수동 실행 시에는 실행 중인 터미널에서 `Ctrl+C`로 종료할 수 있습니다.

실패 시 기본 복구:
- Python 자체가 없으면 Python 3 설치 후 다시 `.\run_doc_rag.bat`
- requirements 설치가 실패하면 네트워크 또는 사내 패키지 미러 접근 상태 확인
- LM Studio/model 미준비 상태면 기본 질의는 실패할 수 있으므로 현재 로드한 모델명을 `LLM_MODEL`과 맞춘 뒤 다시 시도
- 임베딩 모델 캐시가 없으면 `DOC_RAG_EMBEDDING_MODEL`에 로컬 경로 지정

릴리즈 직전에는 [RELEASE_WEB_MVP_CHECKLIST.md](/Users/Agent/ps-workspace/trunk_rag/docs/RELEASE_WEB_MVP_CHECKLIST.md)를 기준으로 점검합니다.

## Optional Desktop Launcher

기본 운영 경로는 계속 브라우저 UI이지만, `desktop/electron`에 선택형 Electron 데스크톱 런처를 유지합니다.

```powershell
cd <repo>\desktop\electron
npm install
npm run check
npm run preflight
npm run smoke
npm start
```

또는 루트에서 바로:

```powershell
cd <repo>
.\run_doc_rag_desktop.bat
```

- `npm run preflight`는 repo 경로, Python 런타임, `app_api` import, 기존 `/health`, 기본 LLM 런타임 도달 여부를 먼저 점검합니다.
- `npm run smoke`는 `.venv`의 Python 또는 시스템 Python으로 `app_api.py`를 띄운 뒤 `/health` readiness를 확인합니다.
- `npm start`는 같은 런타임을 Electron 창에 연결해 `/intro`를 엽니다.
- Electron 앱 시작 시에도 같은 preflight를 먼저 실행하고, blocking 실패가 있으면 창에서 바로 이유를 보여 줍니다.
- `run_doc_rag_desktop.bat`는 preflight를 먼저 실행하고, 통과 시 Electron 런처를 시작합니다.
- 현재 데스크톱 경로는 설치형 제품이 아니라 "기존 웹 UI를 앱 창으로 여는 선택형 런처" 수준입니다.
- 결론과 리스크는 `docs/reports/DESKTOP_WRAPPER_POC_REPORT_2026-03-17.md`를 기준으로 봅니다.
- 패키징/배포 하드닝 재검토 결과는 `docs/reports/DESKTOP_PACKAGING_HARDENING_REVIEW_2026-03-17.md`를 기준으로 보며, 현재 판단은 "보류 유지"입니다.

## Quality Evaluation

등록된 문서 기준으로 `/query` 응답의 완성도를 보려면 answer-level 평가 하네스를 사용합니다.

```powershell
.venv\Scripts\python.exe scripts\eval_query_quality.py `
  --base-url http://127.0.0.1:8000 `
  --llm-provider ollama `
  --llm-model llama3.1:8b `
  --llm-base-url http://localhost:11434 `
  --output-json docs\reports\query_answer_eval_2026-03-17.json `
  --output-report docs\reports\QUERY_ANSWER_EVAL_REPORT_2026-03-17.md
```

- 기본 fixture는 `evals/answer_level_eval_fixtures.jsonl`을 사용합니다.
- 현재 fixture는 `ops-baseline`과 과거 판단 이력 보존용 `graph-candidate` 질문 일부를 포함합니다.
- 평가 항목은 `must_include`, `must_include_any`, `must_not_include`, 최소 답변 길이, 실제 route header를 기반으로 점수화됩니다.
- 현재 `/query`는 최대 2개 컬렉션까지만 직접 선택 가능하므로, 3개 이상 컬렉션이 필요한 graph 질문은 vector baseline 평가 시 `collection=all`로 fallback 합니다.
- 이 스크립트는 GraphRAG 자체를 평가하는 것이 아니라, 현재 Vector RAG 기본 경로의 answer-level 기준선을 만드는 용도입니다.
- `2026-03-18` 기준 최신 baseline은 `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`이며, 6개 fixture 중 2개만 통과했습니다.
- 같은 실측에서 `GQ-03`은 `uk` 컬렉션 인덱스 부재로 `VECTORSTORE_EMPTY`, `GQ-05`는 `fr,ge` 비교 질문에서 `LLM_TIMEOUT`이 발생했습니다.
- 같은 스크립트는 `--backend graph_snapshot`으로 과거 GraphRAG 비교를 재현할 수 있지만, 이 경로는 현재 잠정 중단 상태입니다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md` 기준 `graph-candidate` 3개 케이스는 `2/3 pass`였고, `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md` 기준 최종 판단은 MVP 통합 No-Go였습니다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_OPS_RELIABILITY.md` 기준 `ops-baseline`은 3건 모두 `200` 응답으로 복구됐습니다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` 기준 최신 `ops-baseline`은 `3/3 pass`, `avg_weighted_score=0.9645`, `p95_latency_ms=8724.427`입니다.
- 공식 기본 임베딩 `BAAI/bge-m3` 로컬 캐시가 없는 환경에서는 `DOC_RAG_EMBEDDING_MODEL`에 로컬 경로를 주고, `minishlab/potion-base-4M` 계열은 `DOC_RAG_EMBEDDING_DEVICE=cpu`가 필요할 수 있습니다.

기본 회귀 게이트는 아래 한 명령으로 확인할 수 있습니다.

```powershell
.venv\Scripts\python.exe scripts\check_ops_baseline_gate.py `
  --llm-provider ollama `
  --llm-model llama3.1:8b `
  --llm-base-url http://localhost:11434
```

- 이 스크립트는 `all/eu/fr/ge/it/uk` 컬렉션의 벡터 존재 여부와 `ops-baseline` `3/3 pass`를 함께 확인합니다.
- 실행 순서는 `runtime_preflight -> all-routes collections -> ops-baseline eval`이며, 실패 시 `APP_HEALTH_UNREACHABLE`, `COLLECTIONS_CHECK_FAILED`, `OPS_EVAL_FAILED` 진단 코드를 함께 출력합니다.
- `runtime_preflight`는 이제 `/health`의 `runtime_profile_*`와 같은 기준으로 현재 모델을 `verified / experimental / not_recommended`로 판정합니다.
- `/health`는 `runtime_query_budget_profile`, `runtime_query_budget_summary`, `embedding_fingerprint_status`도 함께 노출합니다.
- `embedding_fingerprint_status=mismatch` 또는 `missing`이면 reindex 후 다시 게이트를 실행하는 것이 기본 복구 경로입니다.
- `2026-03-21` 현재 로컬 검증에서는 앱 미기동 상태에서 `APP_HEALTH_UNREACHABLE`로 즉시 막히는 것을 확인했습니다.
- 과거 `2026-03-21` 실측에서는 `env HF_HUB_OFFLINE=1 ./.venv/bin/python build_index.py --reset` 뒤 `ollama + llama3.1:8b` 게이트가 `3/3 pass`, `avg_weighted_score=0.9645`, `p95_latency_ms=13501.527`로 통과했습니다.
- 프로젝트 기본 경로는 `Ollama` 기준이며, 로컬 환경에 따라 `LM Studio` OpenAI 호환 경로를 별도 실측할 수 있습니다.
- `2026-03-21` 로컬 PC 실측에서는 `LM Studio` `qwen3.5-4b-mlx-4bit` + `http://127.0.0.1:1337/v1` 연결은 확인됐지만 `ops-baseline`은 `LLM_TIMEOUT`으로 `3/3` 실패했습니다.
- 종료 코드 `0`은 게이트 통과, `1`은 컬렉션 비어 있음 또는 eval 실패를 뜻합니다.

## Roadmap Harness

세션 재진입 시 현재 실행 큐와 active 항목을 확인하려면 아래 명령을 사용합니다.

```powershell
.venv\Scripts\python.exe scripts\roadmap_harness.py status
.venv\Scripts\python.exe scripts\roadmap_harness.py validate
```

- `status`는 현재 `active` 항목, 기본 게이트 명령, 큐 상태를 출력합니다.
- `validate`는 `TODO.md`의 `Execution Queue`와 `NEXT_SESSION_PLAN.md`의 `Session Loop Harness`가 일치하는지 검사합니다.
- 현재 규칙은 `active` 항목 1개만 허용하고, `current_active_id`가 실제 active row와 일치해야 합니다.

## API

- `GET /health`: 서버/벡터 상태 확인
- `GET /collections`: 컬렉션별 벡터 수/cap 사용률 조회
- `POST /reindex`: 문서 재인덱싱
- `POST /query`: 질의(기본 단일 컬렉션, 필요 시 최대 2개 컬렉션 선택)
- `GET /rag-docs`: RAG 대상 문서 목록
- `GET /rag-docs/{doc_name}`: 문서 원문(md) 조회
- `POST /admin/auth`: 관리자 인증 코드 확인
- `GET /upload-requests`: 업로드 요청 목록/상태 조회
- `POST /upload-requests`: 일반 사용자 업로드 요청 생성
- `POST /upload-requests/{id}/approve`: 관리자 승인
- `POST /upload-requests/{id}/reject`: 관리자 반려
- 운영 기준은 `docs/UPLOAD_ADMIN_WORKFLOW.md`를 따른다.
- `GET /rag-docs`는 repo의 seed 문서와 승인된 managed active 문서를 함께 반환한다.
- `POST /upload-requests`는 선택적으로 `request_type`, `doc_key`, `change_summary`를 받을 수 있다.
- `POST /upload-requests/{id}/reject`는 `reason_code`, `decision_note`를 함께 받을 수 있다.
- `DOC_RAG_AUTO_APPROVE`는 `create` 요청에만 적용되고 `update` 요청은 항상 관리자 승인 경로를 사용한다.
- GraphRAG는 기본 경로가 아니며, 관련 PoC/실측은 아카이브 상태로만 유지한다.

`POST /reindex` 응답의 `validation`에는 기계 판독용 필드와 함께
`summary_text`(예: `total=5, usable=5, rejected=0, warnings=0, usable_ratio=100.00%`)가 포함됩니다.

`GET /health` 응답에는 현재 적용 중인 `chunking_mode`(`char` 또는 `token`)와
`embedding_model`, `query_timeout_seconds`, `max_context_chars`, `default_llm_provider`,
`default_llm_model`, `default_llm_base_url`가 포함됩니다.
브라우저 기본 모드는 이 값을 받아 권장 LLM 설정을 자동 적용하고,
`고급 설정 펼치기`를 누른 경우에만 provider/model/base URL/API key를 직접 수정합니다.
현재 기본 `max_context_chars`는 미설정 시 `1500`입니다.
`POST /reindex` 응답에는 실제 인덱싱에 사용된 `chunking` 설정이 포함됩니다.
`POST /query`에서 `collection`/`collections`를 명시하지 않으면 키워드 기반 자동 라우팅이 동작하고,
복수 국가 키워드가 동시에 감지되면 최대 2개 컬렉션까지 함께 조회합니다.

예시:

```powershell
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"각 국가별 대표적인 과학적 성과\",\"collection\":\"all\",\"llm_provider\":\"ollama\",\"llm_model\":\"llama3.1:8b\",\"llm_base_url\":\"http://localhost:11434\"}"
```

### `/query` 에러 응답 규격

- 성공 응답은 기존과 동일:
```json
{
  "answer": "...",
  "provider": "ollama",
  "model": "llama3.1:8b"
}
```

- 실패 응답은 `flat + detail` 호환 포맷:
```json
{
  "code": "LLM_TIMEOUT",
  "message": "LLM 응답 시간이 제한(30초)을 초과했습니다.",
  "hint": "모델 상태를 확인하거나 더 짧은 질문으로 다시 시도하세요.",
  "request_id": "uuid-or-client-id",
  "detail": "LLM 응답 시간이 제한(30초)을 초과했습니다."
}
```

- 타임아웃은 기본 `30초`이며 `DOC_RAG_QUERY_TIMEOUT_SECONDS`로 조정할 수 있습니다.

업로드 요청 생성 예시:

```powershell
curl -X POST http://127.0.0.1:8000/upload-requests `
  -H "Content-Type: application/json" `
  -d "{\"source_name\":\"new_doc.md\",\"collection\":\"fr\",\"request_type\":\"create\",\"doc_key\":\"new_doc\",\"change_summary\":\"초안 등록\",\"country\":\"france\",\"doc_type\":\"country\",\"content\":\"## 제목\\n본문\"}"
```

- 실패 코드 매핑:
  - `INVALID_REQUEST` -> `422`
  - `VECTORSTORE_EMPTY` -> `400`
  - `VECTORSTORE_EMBEDDING_MISMATCH` -> `409`
  - `INVALID_PROVIDER` -> `400`
  - `LLM_CONNECTION_FAILED` -> `502`
  - `LLM_TIMEOUT` -> `504`
  - `INTERNAL_ERROR` -> `500`

- `X-Request-ID` 헤더:
  - `/query`의 성공/실패 응답 모두 포함
  - 요청에 `X-Request-ID`를 보내면 같은 값 재사용
  - 없으면 서버가 UUID 생성

- `X-RAG-Collection` 헤더:
  - 실제 질의에 사용된 컬렉션 이름을 반환

- `X-RAG-Collections` 헤더:
  - 실제 질의에 사용된 전체 컬렉션 목록을 반환
  - 자동 다중 라우팅이면 최대 2개 컬렉션이 쉼표로 연결된다

## Preprocessing Contract (정책)

현재 정책:
- `trunk_rag`는 전처리된 md를 입력으로 사용한다.
- 전처리 가이드/규칙은 `docs/PREPROCESSING_RULES.md`를 기준으로 한다.
- 외부 전처리 프롬프트 템플릿은 `docs/PREPROCESSING_PROMPT_TEMPLATE.md`를 사용한다.
- 메타데이터 형식은 `docs/PREPROCESSING_METADATA_SCHEMA.json`을 따른다.

현재 적용 정책:
- 문서 등록 또는 인덱싱 전 검증을 수행하고 `usable=true/false` 판정을 제공한다.
- 불가(`usable=false`) 문서는 벡터스토어에 반영하지 않는다.

참고:
- 본 정책의 상세 운영 기준은 `docs/FUTURE_EXTERNAL_CONSTRAINTS.md`에 정리한다.

## Environment

`.env.example`를 복사해 `.env` 생성 후 사용.

- 기본 예시는 `LLM_PROVIDER=ollama`, `LLM_MODEL=llama3.1:8b`
- 로컬 기본 경로에서는 `OLLAMA_BASE_URL=http://localhost:11434`
- 오프라인 운영 시에는 `DOC_RAG_EMBEDDING_MODEL`로 지정한 경로 또는 `BAAI/bge-m3` 로컬 캐시가 필요
- LM Studio 로컬 경로를 쓰려면 서버가 열려 있고 원하는 모델이 로드되어 있어야 함

- OpenAI 사용 시: `OPENAI_API_KEY`
- Groq 사용 시: `GROQ_API_KEY`, `GROQ_BASE_URL`
- LM Studio 사용 시: `LMSTUDIO_BASE_URL`, `LMSTUDIO_API_KEY`
- Ollama 사용 시: `OLLAMA_BASE_URL`
- Ollama 응답 길이 제한(선택): `DOC_RAG_OLLAMA_NUM_PREDICT` (예: `8`, 미설정 시 모델 기본값)
- 관리자 모드 인증 코드(선택): `DOC_RAG_ADMIN_CODE` (기본값: `admin1234`)
- 개인 운영 자동 승인(선택): `DOC_RAG_AUTO_APPROVE` (`1/true/on`이면 요청 생성 즉시 승인/인덱싱)
- 질의 타임아웃(선택): `DOC_RAG_QUERY_TIMEOUT_SECONDS` (기본 `30`, 단위 초)
- 컨텍스트 길이 제한(선택): `DOC_RAG_MAX_CONTEXT_CHARS` (미설정 시 제한 없음)
- 청킹 모드(선택): `DOC_RAG_CHUNKING_MODE` (`char` 기본, `token` 옵션)
- 토큰 인코딩(선택): `DOC_RAG_CHUNK_TOKEN_ENCODING` (기본 `cl100k_base`)
- 임베딩 모델(선택): `DOC_RAG_EMBEDDING_MODEL` (기본 `BAAI/bge-m3`, 로컬 경로 가능)
- 임베딩 디바이스(선택): `DOC_RAG_EMBEDDING_DEVICE` (예: Apple Silicon 로컬 모델은 `cpu` 권장)

## Local Hardware Guidance

로컬 LLM 경로는 "연결 가능"보다 "ops-baseline 게이트를 시간 제한 안에 안정적으로 통과하는지"를 기준으로 판단합니다.

- 현재 실측 기준 운영 권장 프로파일은 `groq + llama-3.1-8b-instant`입니다.
- 로컬 Ollama 기준에서는 `llama3.1:8b + DOC_RAG_QUERY_TIMEOUT_SECONDS=30`이 최소 통과 프로파일이었습니다.
- `qwen3.5:4b`, `qwen3.5:9b`, `LM Studio qwen3.5-4b-mlx-4bit`는 현재 로컬 Mac mini Pro 실측에서 `ops-baseline`을 안정 통과하지 못했습니다.
- `/health`의 `runtime_profile_status/message/recommendation`과 `runtime_preflight` 결과를 보면 현재 프로파일이 기본 운영 경로로 적합한지 바로 판단할 수 있습니다.
- `/intro`와 `/app` 화면도 같은 `runtime_profile_*` 값을 바로 보여 주므로, 브라우저만 열어도 현재 모델이 `verified / experimental / not_recommended`인지 확인할 수 있습니다.
- `ollama ps`가 불안정하거나 offload 상태를 바로 보기 어려우면 `scripts/diagnose_ollama_runtime.py`로 직접 prompt 처리량을 재서 모델 처리량을 먼저 확인할 수 있습니다.

로컬 하드웨어 권고선(추론):
- 최소 로컬 운영선: Apple Silicon `M4 Pro` 급 + `64GB unified memory`
- 현실적인 권장선: `Mac Studio M4 Max` 급 + `64GB` 이상
- 그 아래 구성은 엣지 실험 경로로는 가능하지만, 현재 `trunk_rag` 운영 프로파일 기준으로는 비권장입니다.

운영 판단 메모:
- 현재 RAG 경로는 단순 채팅이 아니라 `retrieval + context build + 설명형 answer generation` 조합이어서 메모리 대역폭과 토큰 생성 속도 영향을 크게 받습니다.
- 로컬 모델은 `ollama ps` 기준 `100% GPU`에 가깝게 올라가지 않으면 응답 지연이 크게 흔들릴 수 있습니다.
- 이 환경처럼 `ollama ps` 자체가 불안정하면 아래 직접 진단 스크립트로 `eval_tokens_per_second`와 wall time을 우선 확인합니다.

```powershell
.venv\Scripts\python.exe scripts\diagnose_ollama_runtime.py `
  --base-url http://localhost:11434 `
  --model llama3.1:8b `
  --repeat 3
```

- 출력의 `assessment=slow`면 context-heavy RAG에서 timeout 가능성이 크고, `borderline`이면 짧은 context에서만 버틸 수 있으며, `promising`이면 로컬 RAG 후보로 볼 수 있습니다.
- 오프라인/로컬 운영이 반드시 필요하면 모델 선택보다 먼저 하드웨어와 timeout/profile을 함께 설계해야 합니다.

운영 기본값 결정 메모(2026-03-15):
- 기본 청킹 모드는 계속 `char`를 사용합니다.
- `token_800_120`은 로컬 벤치에서 소폭 더 빨랐지만, 샘플 질의 품질 차이가 없어 기본값을 바꾸지 않았습니다.
- 교차 국가 비교 질의는 `all` 고정보다 자동 다중 라우팅(최대 2개 컬렉션)을 기본 경로로 둡니다.
- 관련 근거는 `docs/reports/QUERY_E2E_CHAR_VS_TOKEN_REPORT_2026-03-14.md`,
  `docs/reports/QUERY_QUALITY_ROUTE_REPORT_2026-03-15.md`에 정리했습니다.

## UI 기본 동작

- 기본 질의 모드에서는 `/health`의 런타임 기본 LLM 설정을 자동 사용합니다.
- `고급 설정 펼치기`를 눌러야 provider/model/base URL/API key를 직접 수정할 수 있습니다.
- `vectors=0`이면 질문 전 `Reindex`를 먼저 실행하라는 안내가 표시됩니다.
- 업로드 요청에서 `Source Name`은 비워둘 수 있고, `country`/`doc_type`은 컬렉션 기준 기본값을 따를 수 있습니다.

## Testing

개발용 테스트 의존성 설치:

```powershell
.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.venv\Scripts\python.exe -m playwright install chromium
```

Electron PoC 검증:

```powershell
cd <repo>\desktop\electron
npm run check
npm run preflight
npm run smoke
```

실행:

```powershell
.venv\Scripts\python.exe -m pytest -q
```

개별 실행:

```powershell
.venv\Scripts\python.exe -m pytest -q tests/api
.venv\Scripts\python.exe -m pytest -q tests/test_chunking_modes.py
.venv\Scripts\python.exe -m pytest -q tests/e2e/test_web_flow_playwright.py -m e2e
```

다중 컬렉션 PoC 벤치(검색 단계):

```powershell
.venv\Scripts\python.exe scripts\benchmark_multi_collection.py --reindex --rounds 5 --output docs\reports\multi_collection_benchmark_2026-02-26.json
```

- 결과 메모: `docs/reports/MULTI_COLLECTION_POC_REPORT_2026-02-26.md`

토큰 청킹 PoC 벤치(분할 단계):

```powershell
.venv\Scripts\python.exe scripts\benchmark_token_chunking.py --rounds 5 --output docs\reports\token_chunking_benchmark_2026-02-27.json
```

- 결과 메모: `docs/reports/TOKEN_CHUNKING_POC_REPORT_2026-02-27.md`

`/query` E2E 벤치(LLM 포함, API 기준):

사전 점검:

```powershell
.venv\Scripts\python.exe scripts\runtime_preflight.py --base-url http://127.0.0.1:8010
```

- `blocked`가 나오면 `DOC_RAG_EMBEDDING_MODEL`, `OLLAMA_BASE_URL`, `vectors=0`, 포트 충돌을 먼저 정리합니다.
- 다른 프로젝트가 `8000` 포트를 쓰고 있으면 이 프로젝트 서버를 다른 포트로 띄우고 같은 `--base-url`를 넘깁니다.

```powershell
.venv\Scripts\python.exe scripts\benchmark_query_e2e.py `
  --base-url http://127.0.0.1:8010 `
  --llm-provider ollama `
  --llm-model llama3.1:8b `
  --llm-base-url http://localhost:11434 `
  --rounds 2 `
  --warmup 1 `
  --query-timeout-seconds 120 `
  --output docs\reports\query_e2e_benchmark_2026-02-27.json
```

- 기본 시나리오: `single_all`, `single_fr`, `dual_fr_ge`
- 출력에는 시나리오별 `latency_success_p95_ms`와 `status_counts`가 포함됩니다.
- `char` vs `token_800_120` 재측정 결과는 `docs/reports/QUERY_E2E_CHAR_VS_TOKEN_REPORT_2026-03-14.md`
  에 정리돼 있습니다.
- 샘플 질의 품질과 자동 다중 라우팅 결과는 `docs/reports/QUERY_QUALITY_ROUTE_REPORT_2026-03-15.md`
  에 정리돼 있습니다.
- 느린 로컬 CPU 환경에서는 아래 런타임 설정을 권장:
  - `DOC_RAG_QUERY_TIMEOUT_SECONDS=90`
  - `DOC_RAG_OLLAMA_NUM_PREDICT=32`
  - `DOC_RAG_MAX_CONTEXT_CHARS=300`

## Vector Store Notes

데이터가 증가하면 속도/품질 저하 우려가 있습니다.

- 속도 리스크: 벡터 수 증가에 따른 검색 지연 증가
- 품질 리스크: 유사하지만 덜 관련된 청크가 상위로 노출(노이즈 증가)

정책:
- 무제한 적재 대신 컬렉션 용량 가이드를 둔다.
- 컬렉션당 cap: `30,000 ~ 50,000 vectors`
- cap은 토큰이 아니라 벡터(청크) 수 기준이다.
- 분야별 컬렉션으로 분할하고 단순 라우팅으로 조회 범위를 제한한다.
- 상세 수치와 대응 단계는 `docs/VECTORSTORE_POLICY.md`를 따른다.
- 라우팅 방식 상세는 `docs/COLLECTION_ROUTING_POLICY.md`를 따른다.
