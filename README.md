[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

<p>
  <img src="web/assets/trunk-rag-wordmark.svg" alt="Trunk RAG - Local-first retrieval for private documents" width="360">
</p>

# Trunk RAG (Local Server)

폐쇄망/로컬 환경에서 사용하는 경량 RAG 서버이며, 현재 목표는 "배포 가능한 웹 MVP" 기준으로 웹 UI 기본 경로를 닫는 것입니다.

현재 버전 기준은 `V1 = RAG product`다. `v1.0.1` 이후에는 `V1.5 = agent-ready runtime` 준비 트랙에서 내부 tool registry, middleware chain, execution trace, agent runtime entry draft를 시작하며, `V2 = Agent-enabled RAG`와 `V3 = Agent system`의 경계는 `VERSION_ROADMAP.md`를 따른다.

- 문서: 전처리 완료된 `data/*.md` 입력
- 기본 번들 문서: 첫 실행 검증용 sample-pack demo/bootstrap corpus이며, 제품 본체 도메인 데이터가 아닙니다.
- 청킹: `##`, `###`, `####` 헤더 기반 + 문자 분할(기본), 토큰 분할(옵션)
- 벡터스토어: Chroma (로컬 폴더)
- LLM: `openai` / `ollama` / `lmstudio` / `groq` 선택(기본 예시: `ollama` + `gemma4:e4b`)
- 인터페이스: FastAPI + 브라우저(`http://127.0.0.1:8000`)
- 업로드 워크플로우: 사용자 요청(`pending`) -> 관리자 승인/반려

## Current Operating Baseline

- 제품 성격: 폐쇄망/로컬 환경용 경량 RAG 웹 서버
- 검증된 기본 경로: `run_doc_rag.bat` -> `/intro` -> `/app`
- 현재 중심 기능: 인덱싱, 질의, 업로드 요청, 관리자 승인, 운영 게이트
- 현재 제품 표기: Trunk RAG SVG mark/wordmark/favicon을 `/intro`, `/app`, `/admin`, README에 적용
- 현재 복구 안내: `/intro`와 `/app`는 기본 화면에 간단 상태를 표시하고, release/runtime/ops 세부 진단은 접힘 패널에서 표시
- 현재 문서 흐름: 기본 번들 문서는 유럽 과학사 sample-pack 데모이며, 사용자 문서는 업로드 요청과 관리자 승인 후 반영
- 현재 relation PoC: graph-lite JSONL 관계 스냅샷/인메모리 검색 계층을 `Quality` 단계의 opt-in context 보조로 연결했으며, `Balanced` 기본 경로에는 자동 적용하지 않음. `/app` 답변의 근거 요약과 실행 상세에서는 `graph-lite=hit|fallback|disabled` 상태를 확인할 수 있음
- 현재 범위 밖: full Neo4j/GraphRAG 운영, 무거운 rerank, 설치형 데스크톱 제품화

현재 문서는 과장된 성능 약속보다 "지금 무엇이 준비돼 있고 어떤 경로가 검증됐는지"를 우선 보여 주는 기준으로 유지합니다.
`/intro`, `/app`, `/ops-baseline/latest`는 최신 운영 게이트 상태를 같은 기준으로 보여 주고, `/app` 답변에는 경량 citation/support label과 graph-lite 상태 요약을 함께 노출합니다.
현재 `/ops-baseline/latest`가 보여 주는 본체 기본 게이트는 `generic-baseline`입니다.

## Operating Model (현행화)

`trunk_rag`는 "가벼운 RAG 런타임" 역할에 집중합니다.

- 현재 제품 경계: `V1` 안정화 + `V1.5` 내부 구조 준비
- 현재 범위 안: 기존 RAG 기능을 깨지 않는 internal tool registry, middleware chain, execution trace, agent runtime entry draft
- 현재 범위 밖: `skill registry`, 사용자용 `agent runtime`, `MCP` 기반 외부 tool orchestration

1. 외부 전처리 단계(별도 프로세스, 클라우드 LLM 포함 가능)
- 원본 소스를 정제해 RAG 정책에 맞는 Markdown으로 변환
- 메타데이터(`source`, `country`, `doc_type`)를 채운 산출물 생성

2. `trunk_rag` 단계(현재 + 다음 우선순위)
- 현재: 정제된 md를 인덱싱/검색/질의
- 현재: 데이터 등록 시 검증(사용 가능/불가 판정) 적용
- 현재: core 기본 컬렉션(`all`)과 sample-pack compatibility 컬렉션을 분리해 운영
- 현재: 승인된 업로드는 `chroma_db/managed_docs/`의 active markdown 원본 기준으로 유지
- 현재: answer-level eval fixture + `/query` 품질 평가 하네스 추가
- 현재: `generic-baseline`/`sample-pack-baseline`/`graph-candidate`로 answer-level 평가 버킷을 분리했다
- 현재: 업로드 관리자 Slice 2 완료(`pending` 기본 필터, update 강조, active 문서 미리보기, reject reason code/decision_note)
- 아카이브: GraphRAG 관련 질문셋/계약/PoC/판단 문서는 `docs/GRAPH_RAG_ARCHIVE_INDEX.md` 기준으로만 유지한다
- 현재: `/reindex`와 `build_index.py --reset` 기본 경로는 core 기본 컬렉션 `all`만 재생성하고, sample-pack route 컬렉션은 compatibility bundle opt-in으로 분리했다
- 현재: core `all`에 들어가는 번들 seed 문서는 첫 실행 demo/bootstrap corpus이며, sample-pack compatibility 평가를 위한 예시 데이터로만 해석한다
- 현재: 본체 회귀 게이트는 `generic-baseline 3/3 pass` 기준으로 유지한다
- 현재: `/query`는 runtime profile 기반 query budget(`single/multi`, `verified/experimental/not_recommended`)을 내부 정책으로 적용한다
- 현재: `/query` context build는 MMR retrieval 뒤에 collection pool에서 lexical match가 강한 문서를 최대 2개까지 보강하고, 이어서 경량 lexical boost와 multi-collection coverage rerank로 문서 순서를 한 번 더 보정한다
- 현재: `debug` trace는 `retrieval_strategy`, `lexical_query_terms`, `hybrid_candidate_merge_applied`, `hybrid_candidate_count`, `hybrid_scan_doc_count`, `hybrid_skipped_collections`, `coverage_rerank_applied`, `coverage_rerank_collection_count`를 남겨 경량 보정 적용 여부와 scan 비용을 확인할 수 있다
- 현재: `services/graph_lite_service.py`는 full GraphRAG를 되살리지 않고 JSONL `entities/relations` 스냅샷을 읽어 relation-heavy 질문 감지, 인메모리 관계 검색, RAG context append contract를 제공한다. `/query`는 `quality` 단계에서만 opt-in으로 graph-lite context를 붙이고, no-hit/snapshot-missing이면 기존 vector context로 fallback한다. 관계형/확산 질문은 핵심 관계 표현을 답변 lead에 보존하도록 보정하며, `/app` 답변 하단에서는 graph-lite hit/fallback/disabled 상태와 relation count를 확인할 수 있다
- 현재: `/health`는 `runtime_query_budget_*`, `embedding_fingerprint_*` 상태를 노출해 경량 경로와 인덱스 호환 상태를 먼저 보여 준다
- 현재: reindex 시 컬렉션별 embedding fingerprint를 저장하고, `/query`는 mismatch를 invoke 전에 먼저 차단한다
- 현재: `services/tool_registry_service.py`는 `search_docs`, `read_doc`, `list_collections`, `health_check`, `reindex`, upload approval 계열을 internal tool 후보로 등록한다
- 현재: `config/actor_policy_manifest.json`, `core/actor_policy_manifest.py`, `services/actor_policy_service.py`가 actor category별 read allowlist/mutation candidate를 해석하는 resolver skeleton을 제공한다
- 현재: `services/tool_middleware_service.py`는 request id, timeout budget, tool allowlist, mutation policy guard, mutation apply guard, unsafe action guard, audit log를 순차 적용하는 internal middleware 실행기 skeleton을 제공하고, explicit allowlist가 없으면 actor policy source를 기본값으로 읽는다
- 현재: `services/tool_trace_service.py`는 tool/middleware 실행 결과를 `v1.5.tool_execution_trace.v1` schema로 고정하고 `actor_category`, `mutation_candidate_tools`, policy flag seed와 `internal/public/persisted` audience별 redaction 함수를 제공한다
- 현재: `PREVIEW_REQUIRED` 응답은 `v1.5.mutation_preview_contract.v1` 기준 `preview_contract`, `v1.5.mutation_preview_seed.v1` 기준 `preview_seed`, `v1.5.mutation_apply_envelope.v1` 기준 draft `apply_envelope`를 함께 반환하고, execution trace는 `v1.5.mutation_audit_record.v1` persisted audit contract와 append-only sink receipt를 함께 남긴다
- 현재: `services/agent_runtime_service.py`는 단일 입력을 actor policy source 기반 allowlist/middleware/trace가 붙은 내부 single-tool runtime 흐름으로 실행하고, mutation candidate에 대해서는 `admin_code`/`mutation_intent`/`apply_envelope`와 local-only `executor_binding` 신호를 middleware gate에 전달한다
- 현재: `services/mutation_executor_service.py`는 preview-confirmed apply 이후에 붙는 executor activation/boundary seam을 제공하고, `reindex`는 operator activation request + durable local audit receipt가 함께 맞을 때 기본 `candidate_stub`, valid explicit binding이 추가되면 `live_binding_stub`, `binding_stage=concrete_executor_skeleton`까지 주어지면 `live_result_skeleton`을 선택한다. `binding_stage=guarded_live_executor`는 explicit local-only path에서만 `index_service.reindex()` 호출 seam을 열고, current top-level runtime은 계속 blocked surface로 유지한다. 이 skeleton/guarded result는 `mutation_executor_result` sidecar로 `reindex_summary`, `audit_receipt_ref`, `rollback_hint`를 고정하고, `mutation_success_promotion` contract로 current blocked-success sidecar와 future top-level apply success surface의 mapping을 남기며, adapter-specific failure taxonomy helper는 future top-level failure surface mapping을 고정한다. pre-execution handoff contract는 actual side effect 전 durable audit receipt, executor router, explicit binding, promotion handoff 순서를 고정하고, fake executor smoke contract는 actual index mutation 없는 success/failure promotion evidence를 고정한다. mutation apply router dry-run contract는 direct `_tool_reindex`와 `index_service.reindex`를 호출하지 않는 blocked apply router evidence를 남기며, `services/tool_middleware_service.py`는 blocked apply result 이후 direct tool handler 전 `mutation_apply_guard_pre_side_effect_router` 위치에서 audit receipt를 먼저 만들고 executor router dry-run을 실행한다. top-level promotion router contract는 executor success/failure sidecar를 future top-level apply `result`/`error` surface로 옮기는 draft evidence를 남기되 current runtime은 계속 blocked surface로 유지한다. upload review는 별도 `boundary_noop`로 유지한다
- 현재: actor별 allowlist/mutation 정책 초안은 `docs/reports/V1_5_ACTOR_ALLOWLIST_POLICY_SOURCE_2026-04-11.md`에 고정했고, resolver skeleton과 admin auth + mutation intent gate, preview/audit contract, preview seed + audit sink skeleton, mutation apply draft/guard까지 반영됐다
- 현재: `mutation_apply_guard`는 preview-confirmed envelope를 검증하고 `PREVIEW_REFERENCE_MISMATCH`, `AUDIT_SINK_RECEIPT_REQUIRED`, `AUDIT_SINK_RECEIPT_INVALID`, `MUTATION_INTENT_SUMMARY_REQUIRED`, `MUTATION_APPLY_NOT_ENABLED`를 분리해 차단한다
- 현재: `services/tool_audit_sink_service.py`는 default `null_append_only`를 유지한 채 `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file`일 때만 local append-only file backend와 stable `sequence_id` receipt를 제공하고, receipt/entry에 `90일` rolling retention과 explicit local-operator prune를 드러내는 nested `ops` contract를 남긴다
- 현재: `scripts/smoke_agent_runtime.py`는 `--opt-in-live-binding`, `--opt-in-live-binding-stage-concrete`, `--opt-in-live-binding-stage-guarded`, `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING=1`, `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING_STAGE`를 지원한다. concrete stage smoke에서는 side-effect-free `live_result_skeleton` evidence를 남기고, guarded stage smoke에서는 explicit local-only `guarded_live_executor` binding으로 `index_service.reindex()`를 호출해 runtime sidecar evidence를 남긴다. guarded stage에서는 runtime sidecar가 없으면 smoke check가 실패한다
- 현재: `services/index_service.py`는 source metadata의 list/dict 값을 보존하되 Chroma ingest 직전에는 JSON 문자열로 정규화해 vectorstore metadata 제약을 만족시킨다
- 현재: guarded executor failure는 `mutation_executor_error` sidecar로 blocked apply response와 `execution_trace.contracts`에 남고, promotion router failure route는 supported reindex error code 기준으로 eligible evidence를 남긴다
- 현재: guarded executor success/failure 이후 `mutation_executor_post_execution` audit record와 `mutation_executor_audit_receipt` sidecar가 남아 pre-executor audit sequence id와 post-executor outcome을 연결한다
- 현재: post-audit checkpoint 결론은 default/public top-level promotion `No-Go`, explicit local-only guarded top-level promotion gate implementation planning `Go`다
- 현재: `executor_binding.top_level_promotion_enabled` 추가 opt-in이 있는 explicit local-only guarded path만 top-level `ok=true` success 또는 eligible failure로 승격할 수 있고, 기본 guarded path는 계속 `MUTATION_APPLY_NOT_ENABLED` blocked surface를 유지한다
- 현재: post-promotion checkpoint 결론은 extra opt-in local-only top-level promotion `Go`, default/public promotion `No-Go`, operator runbook update `Go`다
- 현재: operator runbook은 default blocked, activation check, guarded blocked, guarded top-level promotion command와 pre/post audit sequence 확인 절차를 구분한다
- 현재: post-runbook checkpoint 결론은 local-only operator surface `Go`, default/public promotion `No-Go`, rollback drill planning `Go`다
- 현재: rollback drill plan은 pre-state capture, guarded top-level promotion, audit linkage 확인, rebuild-from-source recovery, post-recovery health/vector check 순서로 고정됐다
- 현재: `scripts/smoke_reindex_rollback_drill.py`는 explicit local env guard, pre-state capture, guarded promotion smoke, rebuild-from-source recovery, post-recovery vector capture를 구조화해 출력한다
- 현재: rollback drill execution evidence는 explicit local env에서 `ok=true`, audit linkage `6 -> 7`, recovery rebuild `37/37`, post-recovery vector count `37`을 확인했다
- 현재: post-rollback-drill checkpoint 결론은 local-only rollback-drilled operator surface `Go`, extra opt-in local-only top-level promotion `Go`, default/public top-level promotion `No-Go`, upload review live execution `No-Go`다
- 현재: public promotion blocker register는 product/API contract, authorization, production audit backend, recovery model, concurrency/job lifecycle, upload review boundary, observability/support, regression scope를 default/public blocker로 고정했다
- 현재: local-only closeout 기준 terminal scope는 `reindex` explicit local-only operator/test surface `Go`, default/public top-level promotion `No-Go`, upload review live execution `No-Go`다
- 현재: post-closeout next-track selection은 public blocker implementation 대신 branch handoff snapshot을 선택했다
- 현재: branch handoff snapshot과 branch publication decision은 2026-04-22 당시 snapshot으로 보존한다
- 현재: 2026-04-27 현행화 시작 시점의 branch는 `codex/loop-034-go-no-go-review`, head `540128a`, `main` 대비 `49` commits ahead였고, 전체 테스트 `239 passed`, 기본 agent runtime smoke `ok=true`를 확인했다
- 현재: 사용자 지시에 따라 branch를 remote에 push하고 draft PR `https://github.com/redsunjin/trunk_rag/pull/5`를 열었다
- 현재: PR #5는 merge commit `537ab29`로 `main`에 병합됐고, 로컬 `main`도 fast-forward 완료됐다
- 다음 우선순위: next-track instruction 대기이며, live scope는 여전히 `reindex` 단일 tool 후보로만 다룬다

비목표(현재 단계):
- 원본 수집/크롤링
- 대규모 자동 재작성 파이프라인
- 무거운 rerank/multi-vector 파이프라인 기본 탑재
- full Neo4j/GraphRAG 통합/sidecar 운영
- 사용자용 agent runtime 또는 MCP 외부 tool orchestration

## Files

- `app_api.py`: FastAPI 앱 엔트리포인트/조립 계층
- `api/routes_*.py`: API/UI 라우트 모듈
- `services/*.py`: 질의/인덱싱/업로드 서비스 모듈
- `services/tool_registry_service.py`: V1.5 internal tool registry skeleton
- `services/actor_policy_service.py`: V1.5 actor category -> allowlist/mutation candidate resolver
- `services/tool_middleware_service.py`: V1.5 internal tool middleware chain skeleton
- `services/tool_trace_service.py`: V1.5 internal tool execution trace contract
- `services/tool_preview_service.py`: V1.5 preview seed helper
- `services/tool_audit_sink_service.py`: V1.5 append-only audit sink protocol/null-memory sink
- `services/mutation_executor_service.py`: V1.5 mutation executor selection seam/noop fallback/reindex candidate stub/upload review boundary noop
- `services/agent_runtime_service.py`: V1.5 internal agent runtime entry draft
- `services/graph_lite_service.py`: local JSONL relation snapshot loader/search/context append PoC
- `services/graph_lite_snapshot_builder.py`: current seed + managed active markdown sources에서 graph-lite JSONL snapshot 생성
- `core/actor_policy_manifest.py`: V1.5 actor policy manifest loader/normalizer
- `core/*.py`: 설정/에러/HTTP 유틸
- `config/actor_policy_manifest.json`: V1.5 actor policy source manifest
- `build_index.py`: 초기 인덱스 생성 스크립트
- `common.py`: 공통 유틸리티
- `web/index.html`: 간단 웹 UI
- `web/intro.html`: 인트로/상태 확인 페이지
- `web/admin.html`: 관리자 상태 페이지(MVP)
- `web/js/*.js`: 프론트엔드 로직 모듈
- `web/styles.css`: 공통 스타일
- `web/assets/*.svg`: Trunk RAG 브랜드 마크, 워드마크, favicon
- `browser_companion/`: 로컬 Trunk RAG 서버에 연결하는 Chrome MV3 side panel companion skeleton
- `scripts/validate_rag_doc.py`: 등록 전 문서 검증 스크립트
- `scripts/benchmark_multi_collection.py`: 단일/다중 컬렉션 검색 비교 벤치
- `scripts/benchmark_token_chunking.py`: char/token 청킹 비교 벤치 스크립트
- `scripts/benchmark_query_e2e.py`: `/query` E2E p95 벤치 스크립트
- `scripts/eval_query_quality.py`: answer-level `/query` 품질 평가 스크립트
- `scripts/compare_rag_quality.py`: 모델 후보별 RAG 품질 비교 게이트 스크립트
- `scripts/build_graph_lite_snapshot.py`: 현재 markdown 원본에서 `chroma_db/graph_lite_snapshot`용 graph-lite snapshot 생성
- `scripts/benchmark_graph_lite_sidecar.py`: graph-lite relation snapshot retrieval PoC 벤치 스크립트
- `scripts/validate_browser_companion_manifest.py`: browser companion manifest/권한 경계 검증 스크립트
- `scripts/smoke_browser_companion_extension.py`: Chrome loaded-extension browser companion smoke helper
- `scripts/check_ops_baseline_gate.py`: core 기본 컬렉션 상태와 `generic-baseline` 회귀 게이트를 한 번에 점검하는 스크립트
- `scripts/bootstrap_web_release.py`: 웹 MVP 기본 경로용 `.env`/`.venv`/requirements 부트스트랩 스크립트
- `scripts/roadmap_harness.py`: `TODO.md`/`NEXT_SESSION_PLAN.md`의 루프 상태와 active 항목을 점검하는 스크립트
- `scripts/runtime_preflight.py`: P1 벤치 전 런타임 준비 상태 점검
- `scripts/smoke_agent_runtime.py`: V1.5 internal agent runtime read-only 성공/write 차단 smoke 점검
- `docs/reports/V1_5_AGENT_READY_RUNTIME_REVIEW_2026-04-10.md`: V1.5 WP1-WP4 통합 검토와 병합 준비 판단
- `docs/reports/V1_5_FOLLOWUP_POLICY_2026-04-10.md`: V1.5 public API/trace persistence/allowlist 후속 정책 판단
- `docs/reports/V1_5_TRACE_REDACTION_POLICY_2026-04-10.md`: V1.5 execution trace 저장/노출 전 redaction 정책 초안
- `docs/reports/V1_5_ACTOR_ALLOWLIST_POLICY_SOURCE_2026-04-11.md`: V1.5 actor category/tool group/mutation gate 정책 초안
- `docs/reports/V1_5_PREVIEW_AUDIT_CONTRACT_2026-04-12.md`: V1.5 preview payload/persisted audit contract 기준
- `docs/reports/V1_5_PREVIEW_SEED_AUDIT_SINK_2026-04-12.md`: V1.5 preview seed helper/append-only audit sink skeleton 기준
- `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md`: V1.5 mutation execution activation go/no-go와 executor follow-up 기준
- `docs/reports/V1_5_MUTATION_EXECUTOR_INTERFACE_DRAFT_2026-04-18.md`: V1.5 mutation executor request/contract/noop default/reindex stub 기준
- `docs/reports/V1_5_DURABLE_MUTATION_AUDIT_BACKEND_SKELETON_2026-04-18.md`: V1.5 local append-only audit backend/stable sequence id 기준
- `docs/reports/V1_5_REINDEX_EXECUTOR_ACTIVATION_SEAM_DRAFT_2026-04-18.md`: V1.5 reindex activation guard/noop fallback/candidate stub 기준
- `docs/reports/V1_5_UPLOAD_REVIEW_EXECUTOR_BOUNDARY_REVIEW_2026-04-18.md`: V1.5 upload review boundary/rollback-audit precondition 기준
- `docs/reports/V1_5_MUTATION_AUDIT_RETENTION_OPS_DRAFT_2026-04-18.md`: V1.5 audit retention/prune operator ownership 기준
- `docs/reports/V1_5_REINDEX_LIVE_READINESS_CHECKLIST_DRAFT_2026-04-19.md`: V1.5 reindex live readiness checklist 기준
- `docs/reports/V1_5_MUTATION_ACTIVATION_SMOKE_EVIDENCE_2026-04-19.md`: V1.5 mutation activation blocked-flow smoke evidence 기준
- `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TEST_STATUS_ROADMAP_2026-04-20.md`: V1.5 reindex live adapter 테스트 현황/로드맵 요약
- `docs/reports/V1_5_REINDEX_ACTIVATION_CHECKPOINT_REVIEW_2026-04-19.md`: V1.5 reindex activation checkpoint verdict 기준
- `docs/reports/V1_5_REINDEX_ACTIVATION_OPERATOR_RUNBOOK_DRAFT_2026-04-19.md`: V1.5 reindex activation local operator runbook 기준
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
- `docs/QUERY_EVAL_QUESTION_SET.md`: generic/sample-pack/graph answer-level 질문셋
- `evals/answer_level_eval_fixtures.jsonl`: answer-level 평가 fixture
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`: Vector RAG 1차 answer-level baseline 실측 결과
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md`: 최신 ops-baseline answer completeness 보정 결과
- `docs/GRAPH_RAG_ARCHIVE_INDEX.md`: GraphRAG archive 문서 진입점
- `docs/GRAPH_LITE_RELATION_SIDECAR_CONTRACT.md`: graph-lite relation sidecar PoC 계약
- `docs/reports/GRAPH_LITE_ACTIVE_DOC_QUALITY_DRILL_2026-04-29.md`: active-doc graph-lite snapshot build/benchmark drill 증거
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-04-29_GRAPH_LITE_ACTIVE_DOC_QWEN.md`: active-doc graph-lite snapshot 기준 qwen Quality answer eval 결과
- `docs/reports/RAG_QUALITY_MODEL_COMPARISON_2026-04-29_GRAPH_LITE_ACTIVE_DOC_QWEN.md`: active-doc graph-lite Quality compare gate 결과
- `docs/reports/GRAPH_LITE_QUALITY_PROMOTION_POLICY_2026-04-29.md`: graph-lite Quality opt-in 승격/운영 정책
- `docs/reports/BROWSER_EXTENSION_COMPANION_REVIEW_2026-04-29.md`: Trunk RAG browser companion extension 가능성 검토
- `docs/reports/BROWSER_COMPANION_POC_SCOPE_GATE_2026-04-29.md`: browser companion extension PoC 범위 게이트
- `docs/reports/BROWSER_COMPANION_EXTENSION_SKELETON_2026-04-29.md`: dependency-free Chrome MV3 companion skeleton 구현 기록
- `docs/reports/BROWSER_COMPANION_LOCAL_SERVER_SMOKE_PLAN_2026-04-29.md`: browser companion loaded-extension smoke 계획
- `docs/reports/BROWSER_COMPANION_LOADED_EXTENSION_SMOKE_2026-04-29.md`: browser companion loaded-extension smoke 증거
- `docs/reports/BROWSER_COMPANION_POST_SMOKE_HARDENING_2026-04-29.md`: browser companion smoke 이후 UI/운영 보강 기록
- `docs/reports/BROWSER_COMPANION_GRAPH_LITE_ENABLED_SMOKE_2026-04-29.md`: graph-lite snapshot server 기준 browser companion Quality smoke 증거
- `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md`: Chrome browser companion 로컬 운영/graph-lite 상태 해석/문제 해결 가이드
- `docs/reports/USER_DOC_RAG_QUALITY_FIXTURE_SEED_2026-04-29.md`: user/operator document 기반 answer-level fixture 후보 seed
- `docs/reports/QUALITY_MODEL_DEFAULT_POLICY_REVISIT_2026-04-29.md`: graph-lite/user-doc 후보 기준 Quality 모델 기본 정책 재검토
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
   - `/intro`는 기본 상태를 먼저 보여 주고, `release_web_status`, 런타임 프로파일, 임베딩 fingerprint, 첫 실행 체크리스트는 접힘 패널에서 확인할 수 있습니다.
   - 완전 오프라인 환경에서는 임베딩 모델 `BAAI/bge-m3`를 사전에 로컬 캐시에 준비하거나 `DOC_RAG_EMBEDDING_MODEL`로 로컬 경로를 지정해야 합니다.
3. 첫 실행이거나 상태 메시지에 `vectors=0`이 보이면 먼저 인덱싱:
   - 브라우저 왼쪽 메뉴에서 `Reindex`를 실행하거나
```powershell
cd <repo>
.venv\Scripts\python.exe build_index.py --reset
```
   - 기본 `Reindex`와 `build_index.py --reset`은 core 기본 컬렉션 `all`만 갱신합니다.
   - 이때 번들 seed 문서는 첫 실행 확인용 sample-pack demo/bootstrap corpus로 `all`에 적재됩니다.
   - sample-pack route 컬렉션까지 같이 맞추려면 `build_index.py --reset --include-compatibility-bundle` 또는 `POST /reindex`의 `include_compatibility_bundle=true`를 사용합니다.
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
- Ollama 기본 경로라면 Ollama 서버, `LLM_MODEL`, 모델 pull/실행 상태를 확인한 뒤 다시 시도
- LM Studio 경로라면 현재 로드한 모델명을 `LLM_MODEL`과 맞춘 뒤 다시 시도
- 임베딩 모델 캐시가 없으면 `DOC_RAG_EMBEDDING_MODEL`에 로컬 경로 지정
- `vectors=0`, `embedding_fingerprint_status=missing|mismatch`이면 `/app`의 `Reindex` 또는 `build_index.py --reset`을 먼저 실행

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
  --llm-model gemma4:e4b `
  --llm-base-url http://localhost:11434 `
  --output-json docs\reports\query_answer_eval_2026-03-17.json `
  --output-report docs\reports\QUERY_ANSWER_EVAL_REPORT_2026-03-17.md
```

- 기본 fixture는 `evals/answer_level_eval_fixtures.jsonl`을 사용합니다.
- 현재 fixture는 본체 기본 게이트용 `generic-baseline`, 샘플팩 호환성 확인용 `sample-pack-baseline`, 과거 판단 이력 보존용 `graph-candidate`를 포함합니다.
- `generic-baseline` fixture는 기본 `all` 컬렉션 하나만으로 통과하는 core runtime 기준을 사용합니다.
- `sample-pack-baseline` fixture는 요청별 `query_profile=sample_pack`을 함께 보내 샘플팩 전용 프롬프트/후처리 호환성을 별도로 측정합니다.
- 평가 항목은 `must_include`, `must_include_any`, `must_not_include`, 최소 답변 길이, 실제 route header를 기반으로 점수화됩니다.
- 평가 요청은 기본적으로 `debug=true`를 사용해 `support_level`, citation 수, source route coverage도 함께 기록합니다.
- 현재 `/query`는 최대 2개 컬렉션까지만 직접 선택 가능하므로, 3개 이상 컬렉션이 필요한 graph 질문은 vector baseline 평가 시 `collection=all`로 fallback 합니다.
- 이 스크립트는 GraphRAG 자체를 평가하는 것이 아니라, 현재 Vector RAG 기본 경로의 answer-level 기준선을 만드는 용도입니다.
- `2026-03-18` 기준 최신 baseline은 `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`이며, 6개 fixture 중 2개만 통과했습니다.
- 같은 실측에서 `GQ-03`은 `uk` 컬렉션 인덱스 부재로 `VECTORSTORE_EMPTY`, `GQ-05`는 `fr,ge` 비교 질문에서 `LLM_TIMEOUT`이 발생했습니다.
- 같은 스크립트는 `--backend graph_snapshot`으로 과거 GraphRAG 비교를 재현할 수 있지만, 이 경로는 현재 잠정 중단 상태입니다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_GRAPH_SNAPSHOT.md` 기준 `graph-candidate` 3개 케이스는 `2/3 pass`였고, `docs/reports/GRAPH_RAG_GO_NO_GO_REVIEW_2026-03-18.md` 기준 최종 판단은 MVP 통합 No-Go였습니다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_OPS_RELIABILITY.md` 기준 `ops-baseline`은 3건 모두 `200` 응답으로 복구됐습니다.
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-19_OPS_ANSWER_COMPLETENESS.md` 기준 최신 `ops-baseline`은 `3/3 pass`, `avg_weighted_score=0.9645`, `p95_latency_ms=8724.427`입니다.
- 공식 기본 임베딩 `BAAI/bge-m3` 로컬 캐시가 없는 환경에서는 `DOC_RAG_EMBEDDING_MODEL`에 로컬 경로를 주고, `minishlab/potion-base-4M` 계열은 `DOC_RAG_EMBEDDING_DEVICE=cpu`가 필요할 수 있습니다.

모델 전환 후보는 단일 게이트가 아니라 비교 품질 게이트로 봅니다.

```powershell
.venv\Scripts\python.exe scripts\compare_rag_quality.py `
  --bucket generic-baseline `
  --bucket sample-pack-baseline `
  --model gemma4:e2b `
  --llm-base-url http://localhost:11434 `
  --output-json docs\reports\rag_quality_model_comparison_2026-04-28_gemma4_e2b.json `
  --output-report docs\reports\RAG_QUALITY_MODEL_COMPARISON_2026-04-28_GEMMA4_E2B.md
```

- 기본 임계값은 `pass_rate=1.0`, `avg_weighted_score>=0.85`, `p95<=20000ms`, `support_pass_rate=1.0`입니다.
- `generic-baseline`만 통과해도 본체 기본 질문은 가능하지만, 모델 기본값 전환은 `sample-pack-baseline` 또는 실제 사용자 문서 질문셋까지 함께 통과한 뒤 결정합니다.
- 비교 게이트가 `blocked`이면 종료 코드 `1`을 반환합니다. 이는 모델 전환 보류 신호이며, 리포트 생성 실패와 구분해서 봅니다.
- 2026-04-28 `gemma4:e2b` 비교 게이트는 `generic-baseline 3/3 pass`였지만 `sample-pack-baseline GQ-05` 실패로 전체 `blocked`였습니다.
- Quality 모드 후보 비교는 `/query` 요청 자체의 `timeout_seconds`와 `quality_mode`를 함께 지정해 실행합니다.

```powershell
.venv\Scripts\python.exe scripts\compare_rag_quality.py `
  --base-url http://127.0.0.1:8010 `
  --timeout-seconds 180 `
  --query-timeout-seconds 120 `
  --quality-mode quality `
  --quality-stage quality `
  --bucket generic-baseline `
  --bucket sample-pack-baseline `
  --model gemma4:e2b `
  --model gemma4:e4b `
  --model qwen3.5:9b-nvfp4 `
  --llm-base-url http://localhost:11434 `
  --output-json docs\reports\rag_quality_model_comparison_2026-04-28_quality_candidates.json `
  --output-report docs\reports\RAG_QUALITY_MODEL_COMPARISON_2026-04-28_QUALITY_CANDIDATES.md
```

- 2026-04-28 Quality 후보 비교에서는 `qwen3.5:9b-nvfp4`가 가장 강한 후보였지만 전체 게이트는 `blocked`였습니다.
- `qwen3.5:9b-nvfp4`는 `5/6 pass`, `avg_weighted_score=0.9364`, `p95_latency_ms=6729.217`였고, 실패는 `GQ-05`의 부분근거/미확인 표현 판정입니다.

답변 피드백은 바로 정식 평가 fixture로 승격하지 않고 후보 큐로 먼저 내보냅니다.

```powershell
.venv\Scripts\python.exe scripts\export_feedback_fixture_candidates.py `
  --output-jsonl docs\reports\query_feedback_fixture_candidates_2026-04-28.jsonl `
  --output-report docs\reports\QUERY_FEEDBACK_FIXTURE_CANDIDATES_2026-04-28.md
```

- 기본 입력은 `chroma_db/query_feedback.jsonl`입니다.
- `negative`, `quality_request` 피드백만 후보가 되며, `--include-positive`를 주면 positive 피드백도 낮은 우선순위 후보로 포함합니다.
- 출력 후보는 `suggested_fixture` 초안을 포함하지만 `must_include`와 `must_include_any`는 사람이 채운 뒤 `evals/answer_level_eval_fixtures.jsonl`로 승격합니다.

기본 회귀 게이트는 아래 한 명령으로 확인할 수 있습니다.

```powershell
.venv\Scripts\python.exe scripts\check_ops_baseline_gate.py `
  --llm-provider ollama `
  --llm-model gemma4:e4b `
  --llm-base-url http://localhost:11434
```

- 이 스크립트는 core 기본 컬렉션 `all`의 벡터 존재 여부와 본체 기본 게이트인 `generic-baseline` `3/3 pass`를 함께 확인합니다.
- 실행 순서는 `runtime_preflight -> core collection readiness -> generic-baseline eval`이며, 실패 시 `APP_HEALTH_UNREACHABLE`, `COLLECTIONS_CHECK_FAILED`, `OPS_EVAL_FAILED` 진단 코드를 함께 출력합니다.
- `runtime_preflight`는 이제 `/health`의 `runtime_profile_*`와 같은 기준으로 현재 모델을 `verified / experimental / not_recommended`로 판정합니다.
- `/health`는 `runtime_query_budget_profile`, `runtime_query_budget_summary`, core `embedding_fingerprint_status`, compatibility bundle fingerprint 상태도 함께 노출합니다.
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
- 현재 다음 품질 트랙은 full Neo4j/GraphRAG 재개가 아니라, 기존 vector/semantic 경로를 보조하는 로컬 graph-lite 관계 스냅샷/검색 PoC입니다.

## API

- `GET /health`: 서버/벡터 상태 확인
- `GET /collections`: 컬렉션별 벡터 수/cap 사용률과 업로드 기본 메타데이터 조회
- `POST /reindex`: 문서 재인덱싱
- `POST /semantic-search`: LLM 호출 없이 Chroma/MMR 기반 빠른 검색 결과 반환
- `POST /query`: 질의(기본 core 컬렉션 `all`, 필요 시 최대 2개 컬렉션 선택)
- `POST /query-feedback`: 답변 피드백을 로컬 append-only JSONL로 저장
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
- `POST /reindex`는 기본적으로 core 컬렉션 `all`만 재생성하며, sample-pack compatibility route까지 함께 갱신하려면 `include_compatibility_bundle=true`를 명시한다.

`POST /reindex` 응답의 `validation`에는 기계 판독용 필드와 함께
`summary_text`(예: `total=5, usable=5, rejected=0, warnings=0, usable_ratio=100.00%`)가 포함됩니다.

`GET /health` 응답에는 현재 적용 중인 `chunking_mode`(`char` 또는 `token`)와
`embedding_model`, `query_timeout_seconds`, `max_context_chars`, `default_llm_provider`,
`default_llm_model`, `default_llm_base_url`가 포함됩니다.
또한 `default_runtime_collection_keys`, `compatibility_bundle_*` 필드로 core 기본 경로와 sample-pack compatibility 범위를 함께 보여 줍니다.
브라우저 기본 모드는 이 값을 받아 권장 LLM 설정을 자동 적용하고,
`고급 설정 펼치기`를 누른 경우에만 provider/model/base URL/API key를 직접 수정합니다.
현재 기본 `max_context_chars`는 미설정 시 `1500`입니다.
`POST /reindex` 응답에는 실제 인덱싱에 사용된 `chunking` 설정이 포함됩니다.
`POST /semantic-search`는 `/query`와 같은 컬렉션 라우팅과 embedding fingerprint guard를 사용하지만 LLM을 호출하지 않습니다.
브라우저 `/app`은 질문 시 이 결과를 먼저 표시하고, 질의 모드에 따라 RAG 답변을 별도 `/query` 요청으로 이어서 생성합니다.
질의 모드는 `semantic`, `balanced`, `quality`입니다.
`semantic`은 LLM 없이 검색 결과만 보여 주며 `/query`에는 사용할 수 없습니다.
`balanced`는 `gemma4:e2b` 빠른 답변을 기본으로 만들고, 복합 비교/근거 부족/문서 미확인 답변은 `quality` 단계로 자동 승격합니다.
`quality`는 선택한 고급 설정 모델로 최대 120초까지 기다립니다.
`POST /query-feedback`는 답변 아래 피드백 버튼에서 호출되며 기본 저장 위치는 `chroma_db/query_feedback.jsonl`입니다.
`POST /query`에서 `collection`/`collections`를 명시하지 않으면 기본적으로 core 컬렉션 `all`을 조회합니다.
sample-pack 키워드 기반 자동 라우팅은 `query_profile=sample_pack`일 때만 호환 경로로 동작하고,
복수 국가 키워드가 동시에 감지되면 최대 2개 컬렉션까지 함께 조회합니다.
명시적 `collection`/`collections` 선택은 `query_profile`과 무관하게 그대로 지원됩니다.
`timeout_seconds`를 요청에 포함하면 해당 요청에서만 기본 timeout을 override할 수 있습니다.

예시:

```powershell
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"각 국가별 대표적인 과학적 성과\",\"collection\":\"all\",\"llm_provider\":\"ollama\",\"llm_model\":\"gemma4:e4b\",\"llm_base_url\":\"http://localhost:11434\"}"

curl -X POST http://127.0.0.1:8000/semantic-search `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"갈릴레오의 영향\",\"collection\":\"all\",\"max_results\":3}"
```

### `/query` 에러 응답 규격

- 성공 응답은 기존과 동일:
```json
{
  "answer": "...",
  "provider": "ollama",
  "model": "gemma4:e4b"
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

업로드 요청 생성 예시(core 기본 경로):

```powershell
curl -X POST http://127.0.0.1:8000/upload-requests `
  -H "Content-Type: application/json" `
  -d "{\"source_name\":\"new_doc.md\",\"collection\":\"all\",\"request_type\":\"create\",\"doc_key\":\"new_doc\",\"change_summary\":\"초안 등록\",\"country\":\"all\",\"doc_type\":\"summary\",\"content\":\"## 제목\\n본문\"}"
```

sample-pack compatibility 컬렉션에 직접 올리는 예시는 별도 호환 경로로만 사용합니다.

```powershell
curl -X POST http://127.0.0.1:8000/upload-requests `
  -H "Content-Type: application/json" `
  -d "{\"source_name\":\"sample_fr.md\",\"collection\":\"fr\",\"request_type\":\"create\",\"doc_key\":\"sample_fr\",\"change_summary\":\"샘플팩 프랑스 문서 초안\",\"country\":\"france\",\"doc_type\":\"country\",\"content\":\"## 제목\\n본문\"}"
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

- 기본 예시는 `LLM_PROVIDER=ollama`, `LLM_MODEL=gemma4:e4b`
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
- graph-lite snapshot 경로(선택): `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR` (미설정 시 `docs/reports/graphrag_snapshot_2026-03-17`; 운영 문서 기반 생성은 `python scripts/build_graph_lite_snapshot.py --output-dir chroma_db/graph_lite_snapshot`)
- 청킹 모드(선택): `DOC_RAG_CHUNKING_MODE` (`char` 기본, `token` 옵션)
- 토큰 인코딩(선택): `DOC_RAG_CHUNK_TOKEN_ENCODING` (기본 `cl100k_base`)
- 임베딩 모델(선택): `DOC_RAG_EMBEDDING_MODEL` (기본 `BAAI/bge-m3`, 로컬 경로 가능)
- 임베딩 디바이스(선택): `DOC_RAG_EMBEDDING_DEVICE` (예: Apple Silicon 로컬 모델은 `cpu` 권장)

## Local Hardware Guidance

로컬 LLM 경로는 "연결 가능"보다 "ops-baseline 게이트를 시간 제한 안에 안정적으로 통과하는지"를 기준으로 판단합니다.

- 외부 API 사용이 가능하면 `groq + llama-3.1-8b-instant`가 가장 낮은 지연을 보였습니다.
- 기존 로컬 Ollama 기본 프로파일은 `gemma4:e4b + DOC_RAG_QUERY_TIMEOUT_SECONDS=30`입니다. 다만 2026-04-28 현재 환경의 재실측에서는 `gemma4:e4b` 기본 게이트가 30초 timeout으로 막힐 수 있음을 확인했습니다.
- `gemma4:e2b`는 저지연 로컬 대안으로 검증됐습니다. 2026-04-28 실측 기준 직접 생성은 `assessment=promising`, `generic-baseline 3/3 pass`, `avg_weighted_score=0.92`, `p95_latency_ms=7288.123~16313.556` 범위였습니다. 기본값 전환은 별도 결정으로 두고, 응답 지연이 우선이면 `gemma4:e2b`를 compact budget으로 사용합니다.
- `qwen3.5:4b-nvfp4`는 더 빠른 실험 후보였지만 `generic-baseline 2/3 pass`였으므로 기본 fallback으로 승격하지 않습니다.
- `qwen3.5:4b`, `qwen3.5:9b`, `LM Studio qwen3.5-4b-mlx-4bit`는 과거 로컬 Mac mini Pro 실측에서 `ops-baseline`을 안정 통과하지 못했습니다.
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
  --model gemma4:e4b `
  --repeat 3
```

저지연 대안 검증은 `--model gemma4:e2b`로 같은 스크립트와 `scripts\check_ops_baseline_gate.py --llm-provider ollama --llm-model gemma4:e2b --llm-base-url http://localhost:11434`를 함께 실행합니다.

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
- 질문을 보내면 `/semantic-search` 결과를 먼저 보여 주고, 선택한 `Semantic`/`Balanced`/`Quality` 모드에 따라 RAG 답변을 생성합니다.
- `Balanced`는 `gemma4:e2b` 빠른 답변을 최대 60초까지 기다린 뒤 필요 시 `Quality` 답변을 추가 생성합니다.
- `Quality`는 선택한 고급 설정 모델로 최대 120초까지 기다립니다.
- 답변 아래 피드백 버튼은 로컬 `chroma_db/query_feedback.jsonl`에 평가를 남기고, `정밀 답변` 버튼은 즉시 quality 단계 답변을 추가 생성합니다.
- RAG timeout이 발생해도 빠른 시맨틱 검색 결과는 화면에 남습니다.
- `/intro`와 `/app`의 release/runtime/ops 진단 상세는 기본 화면을 방해하지 않도록 접힘 패널로 표시합니다.
- 기본 문서 목록에는 첫 실행 확인용 유럽 과학사 sample-pack 데모 문서와 승인된 사용자 문서가 함께 표시될 수 있습니다.
- `vectors=0`이면 질문 전 `Reindex`를 먼저 실행하라는 안내가 표시됩니다.
- 업로드 요청에서 `Source Name`은 비워둘 수 있고, `country`/`doc_type`은 `/collections`가 내려주는 manifest 기반 컬렉션 기본값을 따를 수 있습니다.
- 문서 추가/갱신은 `/app`의 업로드 요청과 관리자 승인 흐름을 사용하며, 삭제/비활성화는 기본 MVP 화면에서 제공하지 않습니다.

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
  --llm-model gemma4:e4b `
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
