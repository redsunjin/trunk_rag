# doc_rag TODO (Next Session Start)

목적:
- 다음 세션에서 바로 착수 가능한 작업 목록을 고정한다.
- `P0`를 먼저 완료하고 이후 `P1`로 넘어간다.

참조:
- `NEXT_SESSION_PLAN.md`
- `SPEC.md`
- `VERSION_ROADMAP.md`
- `docs/reports/VERSION_BOUNDARY_RESET_2026-04-04.md`
- `docs/V1_5_AGENT_READY_PLAN.md`
- `docs/PREPROCESSING_RULES.md`
- `docs/reports/CODEBASE_EFFICIENCY_REVIEW_2026-02-28.md`
- `docs/NEXT_SESSION_CONTEXT_2026-02-28.md`
- `Graph_Lang도입검토.md`

## Roadmap Loop Harness

상태 모델:
- `active`: 현재 세션에서 기본적으로 수행할 유일한 최상위 항목
- `pending`: 다음 자동 진행 후보
- `blocked`: 외부 결정/검증 blocker 해소 전까지 멈춘 항목
- `done`: 완료 조건과 검증, 문서 반영, 커밋까지 끝난 항목
- `archived`: 잠정 중단 또는 이력 보존용 항목

루프 규칙:
- 최상위 `active` 항목은 항상 정확히 1개만 둔다.
- `진행`, `계속`, `이어서` 요청이 오면 `active` 항목부터 수행한다.
- `active`가 `done`이 되면 가장 먼저 오는 `pending`을 즉시 다음 `active`로 승격한다.
- `blocked`로 옮길 때는 blocker와 재개 조건을 함께 기록한다.
- `archived`는 실행 큐에서 제외하고 이력만 보관한다.

### Execution Queue

| id | status | title | verify |
| --- | --- | --- | --- |
| LOOP-001 | done | 배포형 웹 MVP 게이트 | `./.venv/bin/python -m pytest -q` + `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434` |
| LOOP-007 | active | 범용 RAG 전환 정리 | `./.venv/bin/python -m pytest -q tests/test_collection_service.py tests/test_index_service.py tests/api/test_upload_api.py tests/test_query_service.py tests/api/test_query_api.py` + `./.venv/bin/python scripts/roadmap_harness.py validate` |
| LOOP-002 | done | 단일 부트스트랩/설치 경로 고정 | `./.venv/bin/python -m pytest -q tests/test_runtime_preflight.py tests/api/test_system_api.py` |
| LOOP-003 | done | 첫 실행 성공 경로와 복구 가이드 강화 | `./.venv/bin/python -m pytest -q tests/api/test_query_api.py tests/test_runtime_service.py` |
| LOOP-004 | done | 릴리즈 문서/운영 체크리스트 정리 | `./.venv/bin/python scripts/roadmap_harness.py validate` |
| LOOP-005 | blocked | 데스크톱 패키징 재착수 | `embedded Python` vs `별도 설치` 전략 확정 후 재개 |
| LOOP-006 | archived | GraphRAG 트랙 | `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md` 기준 아카이브 유지 |

## 2026-03-13 우선순위 재정렬

상태:
- 아래의 `P0/P1/P3-Prep` 섹션은 2026-02-28까지의 완료 이력이다.
- 현재 작업은 아래 "현재 우선순위" 섹션을 기준으로 진행한다.
- GraphRAG 관련 구현/평가는 2026-03-20 기준 잠정 중단하고, 기존 문서/PoC는 아카이브로만 유지한다.

## 완료 Loop (LOOP-001)

목표:
- 현재의 "실제 구동 가능한 내부 운영형 MVP"를 "배포 가능한 웹 MVP" 기준으로 끌어올린다.
- 데스크톱 정식 패키징 없이도 웹 UI 기본 경로만으로 설치, 첫 실행, 기본 운영, 장애 복구가 가능해야 한다.

범위:
- 포함: 웹 UI 기본 경로, 로컬 서버 실행, 인덱싱, 질의, 관리자 승인, 운영 문서, 복구 가이드
- 제외: 데스크톱 정식 패키징, GraphRAG 재개, 인증/권한 확장, 분산 배포

완료 기준:
- 설치/실행 경로가 문서와 스크립트 기준으로 1개 기본 경로로 고정된다.
- 새 환경 기준 첫 실행에서 `intro -> app/admin` 진입까지 필요한 준비 항목과 실패 안내가 명확하다.
- `ops-baseline` 회귀 게이트와 기본 부트스트랩 검증이 릴리즈 전 체크리스트로 묶인다.
- 릴리즈/운영 문서가 "개발자 설명"이 아니라 "운영자 배포 가이드" 기준으로 정리된다.

검증:
- `./.venv/bin/python -m pytest -q`
- `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

진행 메모 (2026-03-20):
- `run_doc_rag.bat`를 배포형 웹 MVP 기준 단일 엔트리포인트로 승격했다.
- 첫 실행 시 `scripts/bootstrap_web_release.py`가 `.env`, `.venv`, `requirements.txt` 설치를 자동 준비하도록 추가했다.
- `LOOP-002` 검증(`tests/test_runtime_preflight.py`, `tests/api/test_system_api.py`)까지 통과했다.
- `/health`와 `/query`가 같은 복구 경로(`run_doc_rag.bat`, `/intro`, Reindex, Ollama`)를 안내하도록 정리했다.
- `LOOP-003` 검증(`tests/api/test_query_api.py`, `tests/test_runtime_service.py`, `tests/api/test_system_api.py`)까지 통과했다.
- `docs/RELEASE_WEB_MVP_CHECKLIST.md`를 추가해 릴리즈 전 점검 항목을 단일 문서로 고정했다.
- `LOOP-004`는 문서 기준 완료 상태다.
- `2026-03-21` 실측에서는 앱 기동 후 첫 게이트 실행이 `VECTORSTORE_EMBEDDING_MISMATCH(409)`로 막혔고, all-routes 인덱스가 현재 임베딩 차원과 맞지 않는 상태임을 확인했다.
- 같은 날짜 `env HF_HUB_OFFLINE=1 ./.venv/bin/python build_index.py --reset`으로 all-routes를 다시 생성한 뒤 `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434 --json` 실측은 `pass_rate=1.0`, `avg_weighted_score=0.9645`, `p95_latency_ms=13501.527`로 통과했다.
- 오프라인/폐쇄망 재인덱싱은 HuggingFace cache가 이미 있는 경우 `HF_HUB_OFFLINE=1`을 함께 주는 경로를 운영 복구안으로 본다.
- 제품 기본값은 다시 `Ollama` 기준으로 유지하고, 이 로컬 PC 실측만 `LM Studio` OpenAI/Ollama 호환 경로(`http://127.0.0.1:1337`)를 사용한다.
- `LM Studio` live gate는 `qwen3.5-4b-mlx-4bit`가 실제로 로드되어 있을 때만 통과 여부를 판단할 수 있었다.
- 같은 날짜 `LM Studio` `qwen3.5-4b-mlx-4bit` + `http://127.0.0.1:1337/v1` live gate 실측에서는 runtime/all-routes는 모두 ready였지만 `ops-baseline` 3건이 전부 `LLM_TIMEOUT`으로 실패했다.
- `DOC_RAG_QUERY_TIMEOUT_SECONDS=30`으로 재실험해도 `pass_rate=0.0`, `p95_latency_ms=35668.911`로 여전히 timeout이어서, 현재 blocker는 연결이 아니라 LM Studio 기본 모델의 응답 지연이다.
- `2026-03-21` 기준 `scripts/check_ops_baseline_gate.py`는 `runtime_preflight`를 먼저 실행하고 `APP_HEALTH_UNREACHABLE` / `COLLECTIONS_CHECK_FAILED` / `OPS_EVAL_FAILED` 진단 코드를 함께 출력하도록 보강했다.
- 같은 날짜 로컬 실행에서는 앱 미기동 상태로 `APP_HEALTH_UNREACHABLE`가 즉시 재현됐고, 기존처럼 모호한 `LLM_CONNECTION_FAILED`만 남기지 않도록 정리했다.
- `/query`는 Chroma `InvalidDimensionException`을 `VECTORSTORE_EMBEDDING_MISMATCH(409)`로 매핑하고 Reindex + `DOC_RAG_EMBEDDING_MODEL` 확인 경로를 안내한다.
- 회귀 검증은 `./.venv/bin/python -m pytest -q` -> `69 passed in 7.65s`, `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`까지 확인했다.
- `2026-03-22` 실측에서는 로컬 Ollama/LM Studio의 `4B/9B/12B` 후보가 운영 게이트를 안정 통과하지 못했고, `llama3.1:8b + DOC_RAG_QUERY_TIMEOUT_SECONDS=30`만 `3/3 pass`였다.
- 같은 날짜 `groq + llama-3.1-8b-instant`는 `ops-baseline 3/3 pass`, `avg_latency_ms=709.273`, `p95_latency_ms=831.045`로 가장 안정적인 운영 프로파일이었다.
- 현재 판단상 `trunk_rag`는 Mac mini Pro 급 로컬 엣지 환경만으로 기본 운영을 보장하기 어렵고, 로컬 최소 권고선은 사실상 `M4 Pro + 64GB unified memory` 이상이다.
- `2026-03-22`에는 `/query` 단계별 병목을 분리하기 위해 라우팅, active collection probe, LLM init, context build, invoke timing 로그를 추가했다.
- 같은 날짜 단일 질문(`uk`, 뉴턴 국장 상징) 진단에서는 `qwen3.5:4b` 첫 요청이 `active_collection_probe_ms=6464.292`, `context.elapsed_ms=146.055`, `invoke.invoke_ms=15005.260(timeout)`이었고, 두 번째 요청도 `active_collection_probe_ms=5.556`으로 내려간 뒤 `invoke.invoke_ms=15005.289(timeout)`으로 다시 실패했다.
- 동일 질문에서 `llama3.1:8b`는 `active_collection_probe_ms=4.140`, `context.elapsed_ms=146.360`, `invoke.invoke_ms=14076.086(ok)`이었고, `groq + llama-3.1-8b-instant`는 `active_collection_probe_ms=3.456`, `context.elapsed_ms=28.126`, `llm_init_ms=177.596`, `invoke.invoke_ms=666.962(ok)`였다.
- 현재 실측 결론은 retrieval/context stuffing보다 로컬 LLM invoke 처리량이 주병목이며, 첫 요청의 임베딩 warm-up 비용은 부가 지연이지만 반복 timeout의 주원인은 아니다.
- `2026-03-23` 기준 해결책 1차로 로컬 기본 Ollama 프로파일과 릴리즈 회귀 게이트를 `llama3.1:8b + 기본 timeout 30초`로 승격하고, `qwen3:4b`는 기본값에서 제외했다.
- 같은 날짜 `runtime_preflight`와 `/health`는 현재 provider/model/timeout 조합을 `verified / experimental / not_recommended`로 판정하고, 비권장 로컬 모델이면 권장 프로파일로 바로 유도하도록 보강했다.
- 같은 날짜 `/intro`와 `/app`도 `runtime_profile_*` 경고를 직접 표시하도록 바꿔, 브라우저 기본 경로만으로도 현재 모델 적합성을 즉시 확인할 수 있게 했다.
- 같은 날짜 `scripts/diagnose_ollama_runtime.py`를 추가해 `ollama ps`가 불안정한 환경에서도 직접 prompt 기준 `eval_tokens_per_second`와 wall time으로 로컬 모델 처리량을 진단할 수 있게 했다.
- `2026-03-25` 구현에서는 `index_service`에 Chroma handle 캐시와 vector count snapshot TTL 캐시를 추가해 `/query`의 active collection probe가 매 요청 DB 재생성을 피하도록 정리했다.
- 같은 날짜 `runtime_service.plan_query_budget()`를 추가해 `verified/experimental/not_recommended`와 `single/multi` 조합별 query budget(`k`, `fetch_k`, `max_total_docs`, `max_context_chars`, `generation_budget_profile`)을 내부 정책으로 고정했다.
- 같은 날짜 `/query`는 `X-RAG-Budget-Profile`, `X-RAG-Route-Reason` 헤더를 반환하고, active collection 기준 embedding fingerprint mismatch를 invoke 전에 먼저 차단하도록 보강했다.
- 같은 날짜 reindex는 컬렉션별 embedding fingerprint를 `chroma_db/embedding_fingerprints.json`에 저장하고, `/health`와 `runtime_preflight`는 `runtime_query_budget_*`, `embedding_fingerprint_*`를 함께 노출/검사하도록 정리했다.
- `2026-03-25` 회귀 검증은 `./.venv/bin/python -m pytest -q` -> `98 passed in 5.52s`까지 확인했다.
- `2026-03-29`에는 실제 `.env`를 권장 기본값(`LLM_MODEL=llama3.1:8b`, `DOC_RAG_QUERY_TIMEOUT_SECONDS=30`)으로 다시 맞췄다.
- 같은 날짜 `env HF_HUB_OFFLINE=1 ./.venv/bin/python build_index.py --reset`으로 all-routes를 재생성해 embedding fingerprint 메타데이터를 채웠다.
- 같은 날짜 `/health` 실측은 `runtime_profile_status=verified`, `runtime_query_budget_profile=verified_local_single`, `embedding_fingerprint_status=ready`로 복구됐다.
- 같은 날짜 `./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434` 실측은 `3/3 pass`, `avg_weighted_score=0.9645`, `p95_latency_ms=13694.613`으로 통과했다.
- 같은 날짜 후속 정리로 빈 `DOC_RAG_MAX_CONTEXT_CHARS`를 정상 fallback으로 처리해 불필요한 warning을 제거했고, `app_api.py`/`build_index.py`는 import 전에 `.env`를 읽도록 바꿔 telemetry 비활성화 설정이 더 이른 시점에 적용되게 했다.
- `2026-03-31`에는 `docs/RELEASE_WEB_MVP_CHECKLIST.md`의 권장 게이트 명령을 verified 운영 프로파일(`ollama + llama3.1:8b`) 기준으로 다시 맞춰 공식 릴리즈 문서와 실제 회귀 게이트 기준을 일치시켰다.
- 같은 날짜 `VERSION_ROADMAP.md`를 추가해 현재 제품을 `V1 = RAG product`, 다음 단계를 `V2 = Agent-enabled RAG`, 장기 목표를 `V3 = Agent system`으로 고정했다.
- `V2`의 공식 준비 범위는 `tool registry`, `middleware chain`, `skill registry`, `execution state`, `agent runtime`이며, 이는 `LOOP-001` 종료 이후 후속 트랙으로 본다.
- `V1.5`는 장기 브랜치가 아니라 준비 트랙으로 유지하고, 실제 개발은 최신 `main`에서 분기한 짧은 작업 브랜치로 진행한다.
- `V1.5`의 첫 작업 순서와 브랜치 운영 규칙은 `docs/V1_5_AGENT_READY_PLAN.md`에 고정한다.
- `2026-04-04` 실측에서는 `qwen3.5:9b-nvfp4`, `qwen3.5:4b-nvfp4`가 Ollama API 경유로 `ops-baseline 3/3 pass`를 유지했지만 runtime profile은 여전히 `experimental`로 본다.
- 같은 날짜 `qwen` 계열이 응답 본문에 `Thinking Process`를 섞어 내는 사례를 확인했고, `/query`와 `query_cli.py`는 assistant prefill 기반 `<final_answer>` 계약과 reasoning 누출 제거 후처리를 추가해 본문만 반환하도록 보강했다.
- 타깃 회귀(`tests/test_query_service.py`, `tests/api/test_query_api.py`)와 `qwen3.5:4b-nvfp4` 실질의 `/query` 호출 재검증에서는 reasoning 누출 없이 최종 답변만 남는 것을 확인했다.
- 같은 날짜 범용화 관점 리뷰에서는 현재 구조가 `eu/fr/ge/it/uk` 컬렉션, 유럽사 질문셋, 질문 유형별 후처리에 과도하게 결합돼 있다는 점을 확인했다.
- `docs/reports/GENERIC_RAG_REFOCUS_REVIEW_2026-04-04.md`를 기준으로, `LOOP-001` 이후 첫 분기 작업은 성능 추가 튜닝보다 `범용 RAG 전환 정리`를 우선한다.
- 같은 날짜 추가 정리로 현재까지의 버전 서사와 실제 코드 구조 사이에 `제품 본체 / sample pack / archive` 경계가 흐려져 있었다는 점을 공식 이슈로 기록했다.
- `docs/reports/VERSION_BOUNDARY_RESET_2026-04-04.md`를 기준으로, 이후 문서/구현/평가에서는 유럽 과학사 데이터셋을 제품 본체가 아니라 `sample pack`으로 취급한다.
- `2026-04-04` closeout 기준 공식 검증은 `./.venv/bin/python -m pytest -q -> 108 passed`, `./.venv/bin/python scripts/check_ops_baseline_gate.py --base-url http://127.0.0.1:8010 --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434 --json -> ready=true, pass_rate=1.0, avg_weighted_score=0.9645, p95_latency_ms=12917.239`, `./.venv/bin/python scripts/roadmap_harness.py validate -> ready`로 마감했다.

LOOP-001 개선 실행 순서 (2026-04-01):
1. [x] 문서/인트로 톤 정리 + `/query` 실행 상세(trace/source) 노출
2. [x] 최신 `ops-baseline` 상태를 읽기 전용 API/카드로 노출
3. [x] citation/support label을 경량 메타데이터로 추가
4. [pending] lexical boost 같은 검색 보정은 `LOOP-001` 종료 이후 후보로만 보관

실행 원칙:
- 1, 2는 현재 `배포형 웹 MVP 게이트` 범위 안에서 바로 반영한다.
- 3은 기본 응답 계약을 크게 늘리지 않는 선에서 후속 보강한다.
- 4는 현재 active loop에서 구현하지 않고 로드맵 후보로만 유지한다.

LOOP-007 범위 메모 (2026-04-04 초안):
- 목표: 현재 유럽사 샘플셋 결합을 본체 제품에서 분리하고 `dataset-agnostic local RAG runtime` 방향으로 재정렬한다.
- 포함: 컬렉션 하드코딩 해체 계획, 질의 후처리의 도메인 규칙 제거 계획, 범용 평가셋 초안, 문서 기준 재정렬
- 제외: 대규모 새 검색 스택 도입, GraphRAG 재개, 데스크톱 재착수
- 기준 문서: `docs/reports/GENERIC_RAG_REFOCUS_REVIEW_2026-04-04.md`

## 현재 Active Loop (LOOP-007)

목표:
- 현재 제품 본체를 유럽 과학사 샘플셋 결합에서 분리해 `dataset-agnostic local RAG runtime` 방향으로 재정렬한다.

범위:
- 포함: 컬렉션 하드코딩 해체 계획, 샘플팩/본체 문서 분리, 질문 유형별 후처리 축소, 범용 평가셋 기준 정리
- 제외: 대규모 검색 스택 교체, GraphRAG 재개, 데스크톱 재착수

완료 기준:
- 본체 문서와 샘플 데이터셋 문서가 분리된다.
- 본체 기준의 컬렉션/라우팅/평가 정책이 특정 유럽사 데이터셋을 전제하지 않게 정리된다.
- 샘플 데이터셋 최적화가 본체 기능 진전으로 해석되지 않도록 기준이 고정된다.

검증:
- `./.venv/bin/python -m pytest -q tests/test_collection_service.py tests/test_index_service.py tests/api/test_upload_api.py tests/test_query_service.py tests/api/test_query_api.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

진행 메모 (2026-04-04):
- `config/collection_manifest.json`를 추가해 샘플팩 컬렉션 정의를 코드 상수에서 외부 manifest로 이동했다.
- `core/settings.py`는 default collection key, collection name, keywords, 업로드 기본 메타데이터를 manifest 기준으로 로드하도록 변경했다.
- `services/collection_service.py`의 `default_country/default_doc_type`도 manifest 기반으로 전환해 국가/문서유형 기본값 하드코딩을 제거했다.
- 현재 단계는 동작 유지 목적의 구조 분리 1차이며, `all/eu/fr/ge/it/uk` 키와 기존 라우팅 동작은 그대로 유지한다.
- 타깃 검증은 `17 passed`(`tests/test_collection_service.py`, `tests/api/test_upload_api.py`, `tests/test_index_service.py`)와 `22 passed`(`tests/test_query_service.py`, `tests/api/test_query_api.py`)까지 확인했다.

## 현재 우선순위 P0 (쉬운 RAG 운영 게이트, 완료 2026-03-13)

목표:
- 비개발자/운영자가 최소 설명만으로 실행, 첫 질의, 문서 등록까지 도달할 수 있게 만든다.
- 고급 설정은 유지하되 기본 경로에서는 숨긴다.

### 1) 실행/부트스트랩 단순화
- [x] `run_doc_rag.bat` 개인 PC 경로 fallback 제거 또는 경고 명확화
- [x] 브라우저 오픈 전 `/health` 준비 대기
- [x] 서버 실행 실패 시 다음 행동(venv/python/포트) 안내
- [x] 종료 스크립트/README 실행 흐름 동기화

### 2) 기본값 단일화
- [x] 기본 provider/model/base_url 1세트 확정
- [x] `.env.example`, UI 기본값, 런처 동작을 동일 기준으로 정렬
- [x] `README.md`, `SPEC.md`의 실행/설정 설명 동기화

### 3) 사용자 화면 단순화
- [x] 기본 모드에서 `provider/model/baseUrl/apiKey` 숨김 또는 접기
- [x] 고급 설정 토글 제공
- [x] 빈 인덱스 상태에서 `/reindex` 유도 메시지 제공
- [x] 모델 미실행/연결 실패 시 가이드형 메시지 제공

### 4) 문서 등록 단순화
- [x] `source_name` 자동 제안 또는 비워도 동작하도록 정리
- [x] `country/doc_type` 기본값 자동 추론 강화
- [x] 업로드 성공/보류/반려 후 다음 행동 안내

완료 기준:
- [x] 새 사용자 기준 "실행 -> 상태 확인 -> 샘플 질의 -> 문서 업로드 요청"이 별도 설명 없이 가능하다.
- [x] 기본 모드에서 사용자가 LLM 세부 설정을 직접 수정하지 않아도 된다.

검증:
- [x] `.venv/bin/python -m pytest -q` -> `25 passed in 7.26s` (2026-03-13)

## 현재 우선순위 P1 (성능/품질 게이트, 완료 2026-03-15)

목표:
- 쉬운 RAG 기본 경로가 느리거나 불안정하지 않도록 운영 기본값을 고정한다.

진행 메모 (2026-03-13):
- `scripts/benchmark_token_chunking.py`를 Python 3.9/파라미터 스윕 기준으로 보강했다.
- 토큰 청킹 1차 스윕(`700/80`, `800/120`, `900/120`)은 완료했고 결과는 `docs/reports/TOKEN_CHUNKING_SWEEP_REPORT_2026-03-13.md`에 정리했다.
- `DOC_RAG_EMBEDDING_MODEL` override와 `scripts/runtime_preflight.py`를 추가해 런타임 준비 상태를 사전 점검할 수 있게 했다.
- 초기 blocker였던 로컬 embedding model/base URL 문제는 local benchmark profile로 우회해 재측정을 진행했다.
- `2026-03-14` 재측정으로 local benchmark profile(`llama3.1:8b`, `max_context=300`, `num_predict=32`) 기준 `/query` E2E는 다시 통과했다.
- 같은 profile에서 `token_800_120`은 `char` 대비 p95가 `1.9% ~ 3.1%` 더 빨랐지만, 공식 기본 스택이 아니라서 운영 기본값은 아직 `char` 유지로 본다.
- `2026-03-15` 샘플 질의 품질 비교에서도 `char`와 `token_800_120` 차이는 확인되지 않았다.
- 같은 비교에서 자동 다중 라우팅(`fr,ge`)은 교차 국가 비교 질의 품질을 개선했고, `collection=all` 고정은 같은 질문에서 충분한 답을 주지 못했다.

- [x] 토큰 청킹 파라미터 재탐색 (`chunk_size`, `chunk_overlap`)
- [x] `/query` 지연/품질 균형 재측정 (`DOC_RAG_OLLAMA_NUM_PREDICT`, `DOC_RAG_MAX_CONTEXT_CHARS`)
- [x] 단일/다중 컬렉션 기본 경로 재판정
- [x] 벤치 JSON/리포트 갱신
- [x] 운영 권장 기본값 확정 및 문서 반영

완료 기준:
- [x] 기본 질의 경로 p95와 품질 기준이 문서로 고정된다.
- [x] 기본 모드의 설정값이 임시값이 아니라 운영 권장값으로 정리된다.

검증:
- [x] `.venv/bin/python -m pytest -q` -> `32 passed in 5.29s` (2026-03-15)

## 현재 우선순위 P2 (제품화 후속)

- [x] 데스크톱 래핑(Electron/Tauri) PoC
- [x] 데스크톱 패키징/배포 하드닝 여부 재검토
- [x] 문서 업로드/갱신 관리자 워크플로우 설계
- [x] 문서 업로드/갱신 관리자 워크플로우 구현 1차
- [x] 문서 업로드/갱신 관리자 워크플로우 구현 2차

진행 메모 (2026-03-17):
- `desktop/electron`에 Electron PoC를 추가했다.
- PoC는 기존 FastAPI 서버를 직접 띄우거나 기존 서버에 attach한 뒤 `/intro`를 데스크톱 창으로 연다.
- `npm run preflight`와 앱 시작 전 preflight를 추가해 repo/Python/backend import/기본 LLM 런타임을 먼저 점검하도록 했다.
- `npm run smoke`로 서버 부트스트랩과 `/health` readiness를 검증했다.
- 결론은 "기술적으로 가능하지만 MVP 기본 범위에는 아직 넣지 않고 보류"다.
- 근거 문서는 `docs/reports/DESKTOP_WRAPPER_POC_REPORT_2026-03-17.md`를 기준으로 본다.
- 패키징/배포 하드닝 재검토 결과도 `docs/reports/DESKTOP_PACKAGING_HARDENING_REVIEW_2026-03-17.md`에 고정했다.
- 결론은 "embedded Python/별도 설치 전략이 먼저 결정되기 전까지는 패키징 투자를 보류"다.
- 업로드/갱신 관리자 워크플로우 설계는 `docs/UPLOAD_ADMIN_WORKFLOW.md`에 고정했다.
- 핵심 결정은 "승인 결과를 벡터스토어 직접 추가로 끝내지 말고 managed markdown 원본 + active 버전으로 운영한다"는 점이다.
- 구현 1차에서는 `request_type/doc_key/change_summary`를 업로드 요청에 추가했다.
- 승인된 요청은 `chroma_db/managed_docs/` 아래 버전 파일로 저장되고, active 버전 기준으로 재구성된다.
- `GET /rag-docs`와 `POST /reindex`는 이제 seed 문서 + managed active 문서를 같은 기준으로 본다.
- `DOC_RAG_AUTO_APPROVE`는 `create` 요청에만 적용되고 `update`에는 적용되지 않는다.
- `2026-03-18` 구현 2차에서는 관리자 화면에 `pending` 기본 필터, `update` 강조, active 문서 존재/미리보기, 요청 상세 패널을 추가했다.
- 반려 시 `reason_code`와 `decision_note`를 함께 저장할 수 있게 했고, 목록/검색에서도 이를 사용한다.
- `2026-03-20` 기준 데스크톱 경로는 정식 패키징 대신 선택형 런처로 유지한다.
- 루트 `run_doc_rag_desktop.bat`로 Electron 런처를 바로 열 수 있게 한다.

검증:
- [x] `env PYTHONPYCACHEPREFIX=/tmp/trunk_rag_pycache ./.venv/bin/python -m compileall api services core tests`
- [x] `./.venv/bin/python -m pytest -q tests/api/test_upload_api.py tests/api/test_system_api.py` -> `13 passed in 0.14s` (2026-03-17)
- [x] `./.venv/bin/python -m pytest -q` -> `34 passed in 4.81s` (2026-03-17)
- [x] `./.venv/bin/python -m pytest -q tests/api/test_upload_api.py tests/test_eval_query_quality.py tests/test_graphrag_poc_service.py` -> `15 passed in 0.08s` (2026-03-18)

## GraphRAG 도입 결정 게이트 (잠정 중단, 아카이브)

상태:
- 2026-03-20 기준 GraphRAG 트랙은 잠정 중단 상태다.
- 아래 내용은 도입 판단 이력 보존용이며, 현재 TODO 우선순위에는 포함하지 않는다.

원칙:
- [x] 기본 `/query`는 기존 Vector RAG를 유지한다.
- [x] GraphRAG는 본체 직접 통합이 아니라 사이드카 PoC를 기본안으로 본다.
- [x] AuraDB는 기본안이 아니다. 폐쇄망/로컬 요구가 유지되면 self-managed Neo4j를 우선 검토한다.

착수 전 조건:
- [x] 관계형/다중 홉 질문셋 15~20개 수집
- [x] 현재 Vector RAG 실패 사례와 개선 필요성 문서화
- [x] GraphRAG가 필요한 질문 유형을 운영 질문과 분리

진행 메모 (2026-03-17):
- `docs/GRAPH_RAG_QUESTION_SET.md`에 18개 질문을 `ops-baseline` / `graph-candidate`로 분리해 고정했다.
- 이 문서부터는 "운영 질문은 기존 `/query` 품질 기준", "관계 연결 질문만 GraphRAG 후보"라는 경계를 사용한다.
- `docs/reports/GRAPH_RAG_VECTOR_GAP_REPORT_2026-03-17.md`에 실제 관측된 실패와 구조적 한계를 분리해 정리했다.
- 결론은 "Vector RAG 기본 경로 유지 + graph-candidate 질문군만 sidecar 후보"다.

PoC 범위:
- [x] `md -> entity/relation 추출 -> graph 적재` 최소 파이프라인 정의
- [x] `query router -> graph/vector hybrid retrieval -> fallback` 계약 정의
- [x] 정확도/지연/운영 복잡도 비교표 작성

진행 메모 (2026-03-17):
- `docs/GRAPH_RAG_SIDECAR_CONTRACT.md`에 최소 적재 파이프라인, `POST /query-advanced` 계약, fallback 규칙을 고정했다.
- GraphRAG 준비 문서 기준으로는 "질문셋 -> 실패 사례 -> sidecar 계약"까지 완료됐다.
- `services/graphrag_poc_service.py`와 `scripts/benchmark_graphrag_sidecar.py`로 graph snapshot 기반 retrieval PoC를 추가했다.
- `docs/reports/graphrag_snapshot_2026-03-17/`에 `entities.jsonl`, `relations.jsonl`, `ingest_stats.json`를 생성했다.
- `docs/reports/GRAPH_RAG_ACTUAL_POC_REPORT_2026-03-17.md` 기준 6개 graph-candidate 질문 1차 실측 결과는 `avg_latency_ms=0.068`, `avg_expected_entity_hit_ratio=0.9444`였다.
- 다만 이 수치는 answer 정확도가 아니라 retrieval recall 성격 지표이고, 2-hop 확장이 일부 질문에서 넓게 퍼져 precision 판단은 아직 부족하다.
- `evals/answer_level_eval_fixtures.jsonl`와 `scripts/eval_query_quality.py`를 추가해 answer-level 자동 채점 하네스를 만들었다.
- 현재 하네스는 대표 질문 6개를 `must_include/must_include_any/must_not_include/route header/min_answer_chars` 기준으로 채점한다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md` 기준 Vector RAG 1차 baseline 실측은 완료됐다.
- 같은 실측에서 `pass_rate=0.3333`, `avg_weighted_score=0.593`, `p95_latency_ms=14277.843`이었고, `GQ-03`은 `VECTORSTORE_EMPTY`, `GQ-05`는 `LLM_TIMEOUT`으로 실패했다.
- `2026-03-18` graph snapshot backend answer-level 비교(`docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md`)에서는 `graph-candidate` 버킷이 `2/3 pass`, `avg_weighted_score=0.8444`, `p95_latency_ms=0.074`였다.
- 현재 로컬 컬렉션 상태 확인 결과 `uk=0`, `fr=7`, `ge=7`, `all=37`이어서 `GQ-03` 실패는 실제 `uk` 인덱스 부재로 재현된다.
- GraphRAG 결정 문서는 `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md`에 고정했다.
- 결론은 "graph-candidate 개선 신호는 있으나 MVP/기본 경로 통합은 No-Go, 연구용 sidecar 트랙만 유지"다.

판단 이력:
- [x] 정확도 개선 신호는 일부 확인됐다.
- [x] answer-level eval harness는 준비됐다.
- 보류: 사이드카 장애 시 기본 질의 경로 유지 검증은 잠정 중단으로 추가 진행하지 않는다.
- 보류: 운영 복잡도 증가 평가도 잠정 중단으로 추가 진행하지 않는다.

## 다음 우선순위 P3 (MVP 기본 경로 품질 보정, 완료 2026-03-19)

목표:
- GraphRAG 확장 대신 현재 Vector RAG 기본 경로의 실패/지연 blocker를 먼저 줄이고, answer completeness를 보정한다.

- [x] `uk` 컬렉션이 비어 있는 원인 정리 및 reindex/운영 가이드 보강
- [x] `fr,ge` 명시 다중 컬렉션 질의의 `LLM_TIMEOUT` 재현 및 blocker 완화
- [x] 같은 fixture 기준 ops-baseline 재측정
- [x] ops-baseline answer completeness 보정(`역할/비교/상징` 표현 정합성 개선)

진행 메모 (2026-03-19):
- `/reindex`와 `build_index.py --reset` 기본 경로가 이제 `all/eu/fr/ge/it/uk` 전체를 함께 재생성한다.
- 로컬 임베딩 경로(`/Users/Agent/Documents/huggingface/models/minishlab/potion-base-4M`) 기준 실제 재인덱싱 후 벡터 수는 `all=37`, `eu=9`, `fr=7`, `ge=7`, `it=7`, `uk=7`로 확인했다.
- `DOC_RAG_MAX_CONTEXT_CHARS` 미설정 시에도 기본 `1500`자를 사용하고, 컨텍스트는 문자 예산 안에서 잘라서 구성하도록 바꿨다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_OPS_RELIABILITY.md` 기준 `ops-baseline`은 이제 3건 모두 `200` 응답이며 `LLM_TIMEOUT`과 `VECTORSTORE_EMPTY`는 재현되지 않았다.
- `services/query_service.py`에 질문 유형별 후처리(`역할/비교/상징`)와 혼합 실패 문장 제거를 추가해 답변 표현 정합성을 보정했다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` 기준 최신 `ops-baseline`은 `3/3 pass`, `avg_weighted_score=0.9645`, `p95_latency_ms=8724.427`이다.
- 현재 `ops-baseline` 3건은 blocker 해소를 넘어 answer completeness까지 통과했으므로, 이후 기본 경로 변경 시 회귀 게이트로 유지한다.
- `scripts/check_ops_baseline_gate.py`를 추가해 `all/eu/fr/ge/it/uk` 벡터 상태와 `ops-baseline` `3/3 pass`를 한 번에 점검할 수 있게 했다.

완료 기준:
- [x] `GQ-03`, `GQ-05`가 현재 기본 경로에서 blocker 없이 재측정 가능하다.
- [x] 다음 세션 기준 MVP 기본 경로 품질 보정 우선순위가 문서로 고정된다.

검증:
- [x] `./.venv/bin/python -m pytest -q tests/api/test_system_api.py tests/api/test_query_api.py tests/test_index_service.py tests/test_runtime_service.py` -> `21 passed in 0.14s` (2026-03-19)
- [x] `env DOC_RAG_EMBEDDING_MODEL=/Users/Agent/Documents/huggingface/models/minishlab/potion-base-4M DOC_RAG_EMBEDDING_DEVICE=cpu ./.venv/bin/python scripts/eval_query_quality.py --bucket ops-baseline --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434` -> `pass_rate=0.0`, `avg_weighted_score=0.8261`, `p95_latency_ms=9028.629` (2026-03-19)
- [x] `./.venv/bin/python -m pytest -q tests/test_query_service.py tests/api/test_query_api.py` -> `13 passed in 0.03s` (2026-03-19)
- [x] `env DOC_RAG_EMBEDDING_MODEL=/Users/Agent/Documents/huggingface/models/minishlab/potion-base-4M DOC_RAG_EMBEDDING_DEVICE=cpu ./.venv/bin/python scripts/eval_query_quality.py --bucket ops-baseline --llm-provider ollama --llm-model llama3.1:8b --llm-base-url http://localhost:11434 --output-json docs/reports/query_answer_eval_2026-03-19_ops_answer_completeness.json --output-report docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` -> `pass_rate=1.0`, `avg_weighted_score=0.9645`, `p95_latency_ms=8724.427` (2026-03-19)
- [x] `./.venv/bin/python -m pytest -q` -> `56 passed in 5.62s` (2026-03-19)

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

- [x] 데스크톱 래핑(Electron/Tauri) PoC
- [x] 문서 업로드/갱신 관리자 워크플로우 설계

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
- [x] Track-1: 데스크톱 패키징/배포 하드닝 여부 재검토
- [x] Track-2: 업로드/갱신 관리자 워크플로우 구현 1차
- [x] Track-3: QA/문서 업데이트 전담

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
