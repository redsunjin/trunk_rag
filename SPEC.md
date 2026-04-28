# doc_rag 스펙 문서

## 문서 목적
- 현재까지의 구현 결과를 한 문서로 정리한다.
- 다음 단계의 개발 우선순위를 고정한다.
- 운영 시 필요한 실행/API 기준을 명확히 한다.

## 프로젝트 목표
- 폐쇄망/로컬 환경에서 동작하는 RAG 서버 구축
- 전처리 완료된 `.md` 문서 기반 검색 및 질의응답
- 공통 UI/UX 스타일 재사용으로 서비스 일관성 확보
- 무거운 파이프라인 대신 "가벼운 RAG 런타임" 유지
- 개발자 전용 데모가 아니라 배포 가능한 웹 MVP 기준으로 설치/실행/운영 경로 고정

## 버전 포지셔닝
- 현재 제품 정체성은 `V1 = RAG product`다.
- `V1`의 중심은 인덱싱 + 질의 + 업로드 요청/관리자 승인 + 운영 게이트다.
- `V2 = Agent-enabled RAG`는 `tool/skill/middleware`를 갖춘 단일 agent runtime을 얹는 다음 단계다.
- `V3 = Agent system`은 planner/worker, MCP ecosystem, 다단계 orchestration을 포함하는 장기 단계다.
- 버전 경계와 `V2` 아키텍처 초안은 `VERSION_ROADMAP.md`를 기준으로 유지한다.

## 현재 범위
### 포함
- 로컬 문서 로딩: `data/*.md` (현재 번들 파일은 첫 실행 확인용 sample-pack demo/bootstrap corpus)
- 헤더 기반 청킹: `##`, `###`, `####` + 모드(`char` 기본, `token` 옵션)
- 임베딩 + 로컬 벡터스토어: HuggingFace + Chroma
- LLM provider 선택: `ollama`, `lmstudio`, `openai`, `groq`
- FastAPI 서버 + 브라우저 UI
- `/query` 표준 에러 응답 + 요청 ID 추적
- 컬렉션 라우팅(`collection` 선택 + sample-pack compatibility profile의 키워드 라우팅)
- 컬렉션 상태 조회(`/collections`) + cap 사용률
- 등록 전 문서 검증(`usable/reasons/warnings`) 1차 적용
- 업로드 요청/승인 워크플로우(`pending/approved/rejected`) 1차 적용
- 업로드 관리자 Slice 2(`pending` 기본 필터, update 강조, active 문서 미리보기, reject reason code/decision_note) 적용
- 승인된 업로드를 `chroma_db/managed_docs/`에 저장하고 active 버전 기준으로 재구성
- 업로드 요청의 `request_type/doc_key/change_summary` 필드 지원
- `/rag-docs`와 `reindex`가 seed + managed active 문서를 같은 기준으로 사용
- Electron 패키징/배포 하드닝 재검토 완료(현재 판단: 보류 유지)
- `/health` 기반 런타임 기본 LLM 설정 노출
- `/health` 기반 runtime query budget profile/summary 노출
- 최신 `ops-baseline` 상태 조회(`/ops-baseline/latest`) + intro/app 카드 노출
- `/query` debug 메타의 citation/support label 노출
- `/query` context build의 경량 lexical rerank 적용
- 컬렉션별 embedding fingerprint 저장 및 `/health`/preflight 선검사
- 기본 모드 UI에서 고급 LLM 설정 기본 숨김
- 빈 인덱스/LLM 연결 오류에 대한 가이드 메시지
- API/프론트 최소 회귀 테스트 체계(pytest + Playwright)
- 전처리 규칙 문서(`docs/PREPROCESSING_RULES.md`)
- 실험용 Electron 데스크톱 래퍼 PoC(`desktop/electron`)
- 업로드/갱신 관리자 워크플로우 설계 문서(`docs/UPLOAD_ADMIN_WORKFLOW.md`)
- query eval 질문셋 문서(`docs/QUERY_EVAL_QUESTION_SET.md`)
- answer-level 평가 fixture + `/query` 품질 평가 스크립트(`evals/answer_level_eval_fixtures.jsonl`, `scripts/eval_query_quality.py`)
- Vector RAG answer-level baseline 리포트(`docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`)
- GraphRAG 관련 문서/PoC 아카이브 유지

### 제외(현재 단계)
- 사용자 인증/권한
- 멀티 유저 세션 분리
- 분산/HA 배포
- 관리자 diff/이력 상세 UI
- 데스크톱 정식 제품화/설치 프로그램
- 원본 소스 자동 수집/크롤링
- 대규모 자동 전처리(재작성/요약) 파이프라인 내장
- cross-encoder rerank/multi-vector 기본 탑재
- GraphRAG 통합/sidecar 운영

## 완료된 작업
### 백엔드
- `GET /health`, `POST /reindex`, `POST /query` 구현
- `GET /ops-baseline/latest` 구현
- `GET /collections`, `POST /admin/auth` 구현
- `GET /upload-requests`, `POST /upload-requests` 구현
- `POST /upload-requests/{id}/approve`, `POST /upload-requests/{id}/reject` 구현
- `GET /rag-docs`, `GET /rag-docs/{doc_name}` 구현
- `POST /semantic-search` 구현: LLM 호출 없이 Chroma/MMR 기반 빠른 검색 결과 반환
- 승인된 요청의 managed markdown runtime 저장소/manifest 구현
- `/query` 표준 실패 응답(`code`, `message`, `hint`, `request_id`, `detail`) 구현
- `/query` 타임아웃 정책(환경 기본값 + 요청 단위 `timeout_seconds` override, 재시도 없음) 적용
- `/query` 성공/실패 응답에 `X-Request-ID` 헤더 제공
- `/query` hot path의 Chroma handle/vector count snapshot 캐시 적용
- `/query` budget profile 헤더(`X-RAG-Budget-Profile`, `X-RAG-Route-Reason`) 제공
- `/query` debug 응답의 support level/citation summary 제공
- `/` -> `/intro` 리다이렉트
- `/intro` 인트로 페이지, `/app` 메인 RAG UI 제공
- `/admin` 관리자 상태 페이지 제공(MVP)
- `/styles.css` 경로에서 공통 스타일 제공
- `/assets/{file_name}` 경로에서 SVG/PNG/ICO 브랜드 자산 제공

### RAG 파이프라인
- Markdown 문서 로딩
- 헤더 기준 분할 + 모드별 분할(`char`/`token`)
- 임베딩 생성(`BAAI/bge-m3`)
- Chroma 인덱싱/조회 + MMR 기반 retrieval
- collection pool에서 lexical match가 강한 문서를 소량 합류시키는 light hybrid candidate merge
- 경량 lexical boost로 context 문서 순서 재조정
- multi-collection 질문에서 상위 context가 한 컬렉션에 쏠리지 않게 하는 light coverage rerank
- graph snapshot 기반 entity/relation 추출 PoC(아카이브)

### 품질/검증
- API 회귀 테스트: `tests/api/test_system_api.py`
- API 회귀 테스트: `tests/api/test_query_api.py`
- API 회귀 테스트: `tests/api/test_upload_api.py`
- 청킹 모드 테스트: `tests/test_chunking_modes.py`
- 프론트 E2E 테스트: `tests/e2e/test_web_flow_playwright.py`
- answer-level fixture 검증: `tests/test_answer_level_eval_fixtures.py`
- answer-level eval 스크립트 테스트: `tests/test_eval_query_quality.py`

### LLM 연결
- provider 분기 로직 통합
- 모델/키/베이스 URL 해석 로직 통합

### UI/UX
- 공통 `styles.css` 스타일 패턴을 현재 `web/index.html`에 반영
- Trunk RAG SVG 브랜드 마크/워드마크/favicon 추가 및 intro/app/admin 헤더에 적용
- `/health` release guidance 기반 첫 실행/복구 체크리스트를 intro/app의 접힘 패널에서 제공
- `/intro`와 `/app` 기본 화면은 일반 사용자용 상태/문서 흐름을 우선하고, runtime/release/ops 진단 장문은 접힘 패널로 숨긴다.
- `/app` 사이드바는 설정 아이콘을 사용하고, 제품 로고는 메인 헤더 브랜드 lockup에만 둔다.
- 공통 레이아웃 클래스 적용(`app-container`, `sidebar`, `main-content`, `card`)
- 화면 구성: 좌측(설정/헬스/문서목록), 우측(채팅/MD 뷰어)
- 인트로/관리자 페이지 분리(`web/intro.html`, `web/admin.html`)
- 프론트 로직 모듈 분리(`web/js/shared.js`, `web/js/app_page.js`, `web/js/admin_page.js`)
- 메인 UI 기본 모드에서 런타임 기본 LLM 설정 자동 적용
- `고급 설정 펼치기`로 provider/model/base URL/API key 수동 수정
- `vectors=0` 상태에서 `Reindex` 선행 안내
- 업로드 요청에서 `Source Name` optional + 컬렉션 기준 기본값 사용
- 업로드 요청에서 `Doc Key`, `Request Type`, `Change Summary` optional 입력 지원
- 관리자 화면에서 `doc_key`, `request_type`, `change_summary`, managed version 노출
- 관리자 화면에서 `pending` 기본 필터, `update` 강조, active 문서 미리보기, 요청 상세 패널 제공
- 반려 시 `reason_code` + `decision_note` 저장 지원

### 데스크톱 PoC
- Electron 기반 최소 래퍼 추가(`desktop/electron`)
- 루트 `run_doc_rag_desktop.bat`로 선택형 데스크톱 런처 진입점 추가
- 시작 전 preflight 추가(repo 경로, Python, backend import, 기본 LLM 런타임 점검)
- 기존 `/intro`, `/app`, `/admin` 웹 UI를 재사용
- 로컬 서버 미실행 시 `.venv` 또는 시스템 Python으로 `app_api.py`를 부트스트랩
- 종료 시 Electron이 직접 띄운 Python 프로세스 정리
- 현재 데스크톱 경로는 정식 패키징이 아니라 선택형 앱 런처로 유지

### 구조 분해(P3-Prep 완료)
- `app_api.py`는 앱 조립/예외 처리 중심으로 축소
- 라우트는 `api/routes_*.py`로 분리
- 서비스 로직은 `services/*.py`로 분리
- 설정/에러/HTTP 유틸은 `core/*.py`로 분리

## 핵심 파일
- `app_api.py`: FastAPI 앱 엔트리포인트와 예외 처리
- `api/routes_*.py`: API/UI 라우팅
- `services/*.py`: 인덱싱/질의/업로드 서비스 계층
- `core/*.py`: 설정/에러/HTTP 공통 계층
- `common.py`: 문서/청킹/임베딩/LLM 공통 유틸
- `VERSION_ROADMAP.md`: `V1/V2/V3` 경계와 `V2` agent architecture 초안
- `scripts/validate_rag_doc.py`: 등록 전 문서 검증
- `build_index.py`: 초기 인덱싱 스크립트
- `requirements.txt`: 런타임 의존성
- `requirements-dev.txt`: 테스트/브라우저 의존성
- `run_doc_rag_desktop.bat`: Windows에서 선택형 Electron 데스크톱 런처 실행
- `desktop/electron/*`: Electron PoC 런타임/검증 스크립트
- `desktop/electron/README.md`: 데스크톱 런처 사용 가이드
- `services/graphrag_poc_service.py`: GraphRAG snapshot/benchmark 보조 서비스
- `scripts/eval_query_quality.py`: answer-level `/query` 품질 평가 하네스
- `scripts/check_ops_baseline_gate.py`: runtime preflight + core 기본 컬렉션 상태 + `generic-baseline` 회귀 게이트/diagnostics 점검
- `scripts/bootstrap_web_release.py`: 웹 MVP 기본 경로용 `.env`/`.venv`/requirements 부트스트랩
- `scripts/roadmap_harness.py`: 실행 큐 상태와 현재 active 항목 점검
- `scripts/diagnose_ollama_runtime.py`: Ollama 직접 호출 기준 prompt/eval 처리량 진단
- `evals/answer_level_eval_fixtures.jsonl`: answer-level 자동 채점 fixture
- `docs/reports/QUERY_ANSWER_EVAL_REPORT_2026-03-18_VECTOR_BASELINE.md`: Vector RAG 1차 answer-level baseline 실측
- `web/index.html`: 브라우저 UI
- `web/admin.html`: 관리자 상태 UI
- `web/styles.css`: 공통 스타일
- `web/assets/*.svg`: Trunk RAG 브랜드 마크/워드마크/favicon
- `web/js/*.js`: 프론트 로직 모듈
- `docs/UPLOAD_ADMIN_WORKFLOW.md`: 업로드/갱신 관리자 운영 설계
- `docs/RELEASE_WEB_MVP_CHECKLIST.md`: 배포형 웹 MVP 릴리즈 체크리스트
- `docs/QUERY_EVAL_QUESTION_SET.md`: generic/sample-pack/graph 평가 질문셋
- `docs/GRAPH_RAG_ARCHIVE_INDEX.md`: GraphRAG archive 문서 진입점

## API 계약
### GET `/health`
- 목적: 서버 상태와 벡터 개수 확인
- 응답 예:
```json
{
  "status": "ok",
  "collection_key": "all",
  "collection": "w2_007_header_rag",
  "default_runtime_collection_keys": ["all"],
  "compatibility_bundle_key": "sample_pack",
  "compatibility_bundle_label": "sample-pack 호환 번들",
  "compatibility_bundle_collection_keys": ["eu", "fr", "ge", "it", "uk"],
  "compatibility_bundle_optional": true,
  "seed_corpus_key": "sample_pack_bootstrap",
  "seed_corpus_label": "sample-pack demo/bootstrap corpus",
  "seed_corpus_role": "demo_bootstrap",
  "seed_corpus_dataset": "sample-eu-science-history",
  "persist_dir": "C:/.../chroma_db",
  "vectors": 37,
  "auto_approve": false,
  "pending_requests": 2,
  "chunking_mode": "char",
  "embedding_model": "BAAI/bge-m3",
  "query_timeout_seconds": 30,
  "max_context_chars": 1500,
  "default_llm_provider": "ollama",
  "default_llm_model": "gemma4:e4b",
  "default_llm_base_url": "http://localhost:11434",
  "runtime_query_budget_profile": "verified_local_single",
  "runtime_query_budget_summary": "profile=verified_local_single | k=3 | fetch_k=10 | max_docs=3 | context=1500 | generation=standard | max_output_tokens=192",
  "embedding_fingerprint_status": "ready",
  "compatibility_bundle_embedding_fingerprint_status": "empty"
}
```
- 메인 UI 기본 모드는 `default_llm_*` 값을 자동 사용한다.
- `vectors=0`이면 사용자가 질의하기 전에 `Reindex`를 먼저 실행하도록 안내한다.
- `release_web_status`, `release_web_headline`, `release_web_steps`는 intro/app의 첫 실행/복구 체크리스트에 그대로 사용한다.
- `default_runtime_collection_keys`와 `compatibility_bundle_*`는 core 기본 경로와 sample-pack compatibility 범위를 함께 보여 준다.
- `seed_corpus_*`는 기본 `all` 컬렉션에 적재되는 번들 seed 문서가 첫 실행 demo/bootstrap corpus이며 제품 본체 도메인 데이터가 아님을 보여 준다.
- `embedding_fingerprint_status`는 core 기본 컬렉션 기준이고, `compatibility_bundle_embedding_fingerprint_*`는 sample-pack compatibility bundle 상태를 따로 보여 준다.
- `runtime_query_budget_*`는 현재 기본 런타임이 어떤 경량 query budget으로 동작하는지 보여 준다.
- `embedding_fingerprint_status`가 `mismatch` 또는 `missing`이면 query 전에 reindex를 다시 실행하는 것이 기본 복구 경로다.

### GET `/collections`
- 목적: 컬렉션별 벡터 수/cap 사용률과 업로드 기본 메타데이터 조회
- 응답 예:
```json
{
  "default_collection_key": "all",
  "collections": [
    {
      "key": "all",
      "name": "w2_007_header_rag",
      "label": "전체 (기본)",
      "default_country": "all",
      "default_doc_type": "summary",
      "vectors": 37,
      "soft_cap": 30000,
      "hard_cap": 50000,
      "soft_usage_ratio": 0.0012,
      "hard_usage_ratio": 0.0007,
      "soft_exceeded": false,
      "hard_exceeded": false
    }
  ]
}
```
- `default_country`, `default_doc_type`는 업로드 요청 UI와 서버 기본 메타데이터가 같은 manifest 기준을 쓰도록 노출한다.

### GET `/ops-baseline/latest`
- 목적: 최근 `ops-baseline` 게이트 결과를 읽기 전용으로 조회
- 응답 예:
```json
{
  "status": "ok",
  "ready": true,
  "generated_at": "2026-04-01T00:00:00Z",
  "summary": {
    "cases": 3,
    "passed": 3,
    "pass_rate": 1.0,
    "avg_weighted_score": 0.9645,
    "avg_latency_ms": 6095.881,
    "p95_latency_ms": 8724.427
  },
  "collections_ready": true,
  "runtime_ready": true,
  "missing_keys": [],
  "diagnostics": []
}
```
- 최신 보고서가 없으면 `status=missing`, `ready=false`와 함께 생성 명령 힌트를 반환한다.

### POST `/reindex`
- 목적: seed 문서 + managed active 문서 기준 벡터 재생성
- 요청:
```json
{
  "reset": true,
  "collection": "all",
  "include_compatibility_bundle": false
}
```
- `collection=all` + `include_compatibility_bundle=false`면 core 기본 컬렉션 `all`만 재생성한다.
- sample-pack route 컬렉션까지 함께 맞추려면 `include_compatibility_bundle=true`를 사용한다.
- 응답 예:
```json
{
  "docs": 5,
  "docs_total": 5,
  "chunks": 37,
  "vectors": 37,
  "persist_dir": "C:/.../chroma_db",
  "collection": "w2_007_header_rag",
  "collection_key": "all",
  "reindex_scope": "default_runtime_only"
}
```

### POST `/query`
- 목적: 문서 기반 질의응답
- 요청:
```json
{
  "query": "각 국가별 대표적인 과학적 성과를 요약해줘",
  "collection": "all",
  "llm_provider": "ollama",
  "llm_model": "gemma4:e4b",
  "llm_api_key": null,
  "llm_base_url": "http://localhost:11434",
  "query_profile": "generic",
  "timeout_seconds": 60
}
```
- `collection`/`collections`를 생략하면 기본 core 컬렉션 `all`을 사용한다.
- `query_profile`는 기본 `generic`이며, 샘플팩 호환 평가가 필요할 때만 `sample_pack`을 사용한다. `sample_pack`일 때만 sample-pack 키워드 기반 compatibility 라우팅과 전용 프롬프트/후처리가 활성화된다.
- `debug=true`면 route/budget/stage timing/source/support/retrieval trace 메타를 함께 반환한다.
- retrieval trace에는 `retrieval_strategy`, `lexical_query_terms`, `hybrid_candidate_merge_applied`, `hybrid_candidate_count`, `hybrid_scan_doc_count`, `hybrid_skipped_collections`, `coverage_rerank_applied`, `coverage_rerank_collection_count`, `coverage_rerank_covered_term_count`가 포함된다.
- 응답 헤더:
  - `X-Request-ID`
  - `X-RAG-Collection`
  - `X-RAG-Collections`
  - `X-RAG-Budget-Profile`
  - `X-RAG-Route-Reason`
- `X-RAG-Query-Profile`
- sample-pack compatibility 자동 라우팅은 최대 2개 컬렉션까지 확장한다.
- 키워드가 없거나 과도하게 많이 매칭되면 기본 컬렉션 `all`로 fallback 한다.
- 응답 헤더 `X-RAG-Collection`, `X-RAG-Collections`에 실제 사용 컬렉션이 담긴다.

### POST `/semantic-search`
- 목적: LLM 생성 없이 빠른 시맨틱 검색 fallback 결과를 반환한다.
- 요청:
```json
{
  "query": "갈릴레오의 영향",
  "collection": "all",
  "query_profile": "generic",
  "max_results": 3
}
```
- `/query`와 같은 collection routing, active vector check, embedding fingerprint guard를 사용한다.
- retrieval은 기존 Chroma/MMR + light hybrid/lexical/coverage 계층을 공유한다.
- 응답은 `results[].source`, `h2`, `collection_key`, `snippet`과 `meta.retrieval_strategy`를 포함한다.
- `/app`은 이 결과를 먼저 표시하고, RAG 답변은 별도 `/query` 요청으로 이어서 생성한다.

### POST `/admin/auth`
- 목적: 관리자 인증코드 확인(초기 MVP)
- 요청:
```json
{
  "code": "admin1234"
}
```

### GET `/upload-requests`
- 목적: 업로드 요청 목록 조회(상태 필터 가능)
- 응답 예:
```json
{
  "auto_approve": false,
  "counts": {
    "pending": 2,
    "approved": 1,
    "rejected": 0
  },
  "requests": [
    {
      "id": "uuid",
      "status": "pending",
      "collection_key": "all",
      "source_name": "new_doc.md",
      "doc_key": "new_doc",
      "request_type": "create",
      "change_summary": "초안 등록",
      "usable": true
    }
  ]
}
```

### POST `/upload-requests`
- 목적: 일반 사용자 업로드 요청 생성
- 요청(core 기본 경로):
```json
{
  "source_name": "new_doc.md",
  "collection": "all",
  "request_type": "create",
  "doc_key": "new_doc",
  "change_summary": "초안 등록",
  "country": "all",
  "doc_type": "summary",
  "content": "## 제목\n본문"
}
```
- sample-pack compatibility 컬렉션에 직접 올리는 경우에만 `collection=fr`, `country=france`, `doc_type=country` 같은 샘플팩 메타데이터 예시를 사용한다.
- 응답 예:
```json
{
  "auto_approve": false,
  "request": {
    "id": "uuid",
    "status": "pending",
    "request_type": "create",
    "doc_key": "new_doc",
    "usable": true
  }
}
```
- `request_type`를 명시하지 않으면 현재 active 문서 존재 여부로 `create/update`를 자동 판단한다.
- `request_type=create`인데 같은 `doc_key`가 이미 있으면 `422`를 반환한다.
- `request_type=update`인데 대상 `doc_key`가 없으면 `422`를 반환한다.
- `DOC_RAG_AUTO_APPROVE`는 `create` 요청에만 적용된다.

### POST `/upload-requests/{id}/approve`
- 목적: 관리자 승인 및 인덱싱 반영
- 요청:
```json
{
  "code": "admin1234"
}
```
- 응답 예:
```json
{
  "request": {
    "id": "uuid",
    "status": "approved",
    "managed_doc": {
      "active": true,
      "doc_key": "new_doc"
    },
    "ingest": {
      "mode": "reindex"
    }
  }
}
```

### POST `/upload-requests/{id}/reject`
- 목적: 관리자 반려
- 요청:
```json
{
  "code": "admin1234",
  "reason": "검증 기준 미달"
}
```
- 응답:
```json
{
  "request": {
    "id": "uuid",
    "status": "rejected",
    "rejected_reason": "검증 기준 미달"
  }
}
```
- 실패 응답 예:
```json
{
  "detail": "관리자 인증코드가 올바르지 않습니다."
}
```

### GET `/rag-docs`
- 목적: RAG 대상 문서 목록 조회
- 응답 예:
```json
{
  "docs": [
    {
      "name": "eu_summry.md",
      "size": 12829,
      "updated_at": 1766078655,
      "origin": "seed",
      "doc_key": "eu_summry",
      "collection_key": "eu"
    },
    {
      "name": "new_doc.md",
      "size": 512,
      "updated_at": 1766079999,
      "origin": "managed",
      "doc_key": "new_doc",
      "collection_key": "all"
    }
  ]
}
```

### GET `/rag-docs/{doc_name}`
- 목적: 특정 문서 원문 Markdown 조회
- 응답 예:
```json
{
  "name": "eu_summry.md",
  "content": "## ..."
}
```
- 응답 예:
```json
{
  "answer": "...",
  "provider": "ollama",
  "model": "gemma4:e4b"
}
```

## 실행 기준
- 가상환경 생성(권장):
```powershell
cd <repo>
python -m venv .venv
```
- 런타임 패키지 설치:
```powershell
cd <repo>
.venv\Scripts\python.exe -m pip install -r requirements.txt
```
- 환경 파일 준비(권장):
```powershell
cd <repo>
copy .env.example .env
```
- `.env.example` 기본값은 로컬 우선(`ollama`, `gemma4:e4b`)이며, `OLLAMA_BASE_URL`은 `http://localhost:11434`를 사용한다.
- 임베딩 모델은 `DOC_RAG_EMBEDDING_MODEL`로 override 가능하며, HuggingFace 모델 ID 또는 로컬 경로를 받을 수 있다.
- 로컬 embedding 모델이 `MPS`에서 불안정하면 `DOC_RAG_EMBEDDING_DEVICE=cpu`로 강제할 수 있다.
- 인덱스 생성:
```powershell
cd <repo>
.venv\Scripts\python.exe build_index.py --reset
```
- sample-pack compatibility route까지 함께 재생성하려면:
```powershell
cd <repo>
.venv\Scripts\python.exe build_index.py --reset --include-compatibility-bundle
```
- 서버 실행(권장):
```powershell
cd <repo>
.\run_doc_rag.bat
```
- 런처는 `.venv\Scripts\python.exe` 우선, 없으면 시스템 `python`을 사용한다.
- 런처는 `/health`가 200 응답이 될 때까지 최대 45초 대기한 뒤 `/intro`를 연다.
- `/intro`는 기본 상태를 먼저 보여 주고, release status badge, 첫 실행 체크리스트, 런타임 프로파일, ops-baseline 상태는 접힘 패널에서 확인하게 한다.
- `/app`는 sample-pack 데모 문서와 사용자 문서 추가/갱신 요청 흐름을 먼저 설명하고, 복구/ops 상세는 접힘 패널에서 확인하게 한다.
- 서버 실행(수동):
```powershell
cd <repo>
.venv\Scripts\python.exe app_api.py
```
- 실험용 Electron PoC:
```powershell
cd <repo>\desktop\electron
npm install
npm run check
npm run preflight
npm run smoke
npm start
```
- 첫 실행 또는 `vectors=0` 상태면 `/app` 왼쪽 메뉴의 `Reindex`를 먼저 실행한다.
- `/query`가 `VECTORSTORE_EMBEDDING_MISMATCH(409)`를 반환하면 `Reindex` 또는 `build_index.py --reset`을 다시 실행하고 `DOC_RAG_EMBEDDING_MODEL` 설정을 확인한다.
- UI 접속:
- 인트로: `http://127.0.0.1:8000/intro`
- 메인: `http://127.0.0.1:8000/app`
- 관리자: `http://127.0.0.1:8000/admin`

## 설계 결정 기록
- 실습용 가변 파라미터를 줄이고 운영용 기본값은 `/health`를 통해 UI에 주입
- API 중심 구조 유지(FastAPI)로 UI/앱/확장 연동 재사용성 확보
- 문서 청킹 정책은 `##`, `###`, `####` 고정 + 분할 모드는 `char` 기본 유지
- LLM provider 다중 지원 유지(로컬 우선 + 외부 API 선택), 다만 기본 UX는 로컬 기본값 중심
- `trunk_rag`는 전처리된 md 소비자 역할에 집중
- 전처리는 외부 단계에서 수행하고, `trunk_rag`는 검증 게이트 중심으로 관리
- 쉬운 RAG 기본 경로를 위해 런처 readiness 대기와 고급 설정 기본 숨김 유지
- 교차 국가 비교 질의는 `all` 고정보다 키워드 기반 자동 다중 라우팅(최대 2개)을 기본 경로로 둔다
- 데스크톱은 웹 UI 재작성 대신 기존 FastAPI + 웹 자산을 감싸는 래퍼로만 PoC하고, MVP 본체에는 아직 포함하지 않는다
- 업로드/갱신 운영 기준은 벡터스토어 직접 수정이 아니라 managed markdown 원본 + active 버전 기준으로 가져간다

## 제약 사항
- 추론 속도/품질은 로컬 하드웨어 성능에 크게 의존
- 현재 실측 기준 로컬 최소 운영선은 `8B`급 모델을 `30초` timeout 안에서 통과시키는 수준이며, Apple Silicon에서는 사실상 `M4 Pro + 64GB unified memory` 이상을 권고한다
- `qwen3.5:4b`, `qwen3.5:9b`, `LM Studio qwen3.5-4b-mlx-4bit`는 현재 Mac mini Pro 로컬 실측에서 운영 게이트를 안정 통과하지 못했다
- 클라우드 추론(`groq + llama-3.1-8b-instant`)은 같은 게이트를 매우 낮은 지연으로 통과했으므로, 현행 운영 권장 경로는 로컬 엣지보다 클라우드 추론에 가깝다
- 현재는 단일 노드 운영 기준
- UI는 최소 운영 기능 중심(사이드바/차트/슬라이더 미사용)
- 데이터가 증가할수록 검색 지연과 노이즈 증가 가능
- 폐쇄망/오프라인 운영 시 `DOC_RAG_EMBEDDING_MODEL`로 지정한 로컬 경로 또는 `BAAI/bge-m3` 로컬 캐시와 로컬 LLM 런타임 준비가 선행돼야 함

## 운영 경계(현행)
- 외부 전처리 단계:
  - 원본 소스 정제
  - 헤더/메타데이터 표준화
  - RAG 적합 md 산출
- `trunk_rag` 단계:
  - 산출 md 인덱싱/검색/질의
  - 등록 전 검증으로 사용 가능/불가 판정
  - 분야별 컬렉션 + 최대 2개 자동 다중 라우팅

## 벡터스토어 정책
- 기본 컬렉션(`all`)을 core runtime으로 운영하고, `eu/fr/ge/it/uk`는 sample-pack compatibility 컬렉션으로 유지
- 컬렉션당 cap은 `30,000 ~ 50,000 vectors`
- 벡터 수 증가 시 성능/품질 저하를 방지하기 위해 용량 정책 적용
- 상세는 `docs/VECTORSTORE_POLICY.md` 참조
- 컬렉션 라우팅 방식은 `docs/COLLECTION_ROUTING_POLICY.md` 참조

## 외부 제한사항 연계
- 외부 전처리 파이프라인 제약과 추후 내부 반영 항목은 `docs/FUTURE_EXTERNAL_CONSTRAINTS.md` 참조

## 다음 진행 방향
### 1순위
- MVP 기본 경로 품질 유지
- 내용: `run_doc_rag.bat`를 배포형 웹 MVP 기준 단일 부트스트랩/실행 경로로 유지하고, `/reindex`와 `build_index.py --reset` 기본 경로는 core 컬렉션 `all` 중심으로 유지하며, sample-pack route는 compatibility opt-in으로 분리하고, `generic-baseline`의 `3/3 pass` 상태를 본체 회귀 게이트로 유지한다.

### 2순위
- V1.5 agent-ready runtime 준비
- 내용: 사용자 기본 `/query`를 대체하지 않고 `services/tool_registry_service.py` 기준 internal tool registry skeleton, `services/tool_middleware_service.py` 기준 middleware chain skeleton, `services/tool_trace_service.py` 기준 execution trace 계약, `services/agent_runtime_service.py` 기준 internal agent runtime entry draft를 유지한다. 2026-04-10 통합 검토는 `docs/reports/V1_5_AGENT_READY_RUNTIME_REVIEW_2026-04-10.md`에 기록했고 `main` 병합 후 재검증까지 완료했다. 후속 public API/trace persistence/allowlist 정책은 `docs/reports/V1_5_FOLLOWUP_POLICY_2026-04-10.md`를 따르며, trace 저장/노출 전 redaction 기준은 `docs/reports/V1_5_TRACE_REDACTION_POLICY_2026-04-10.md`, actor별 allowlist/mutation source 및 resolver 기준은 `docs/reports/V1_5_ACTOR_ALLOWLIST_POLICY_SOURCE_2026-04-11.md`, preview/audit contract 기준은 `docs/reports/V1_5_PREVIEW_AUDIT_CONTRACT_2026-04-12.md`, preview seed/audit sink skeleton 기준은 `docs/reports/V1_5_PREVIEW_SEED_AUDIT_SINK_2026-04-12.md`, mutation apply draft/guard 기준은 `docs/reports/V1_5_MUTATION_APPLY_DRAFT_2026-04-12.md`, `docs/reports/V1_5_MUTATION_APPLY_GUARD_2026-04-12.md`, execution activation go/no-go 기준은 `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md`, executor interface draft 기준은 `docs/reports/V1_5_MUTATION_EXECUTOR_INTERFACE_DRAFT_2026-04-18.md`, durable audit backend skeleton 기준은 `docs/reports/V1_5_DURABLE_MUTATION_AUDIT_BACKEND_SKELETON_2026-04-18.md`, `reindex` activation seam 기준은 `docs/reports/V1_5_REINDEX_EXECUTOR_ACTIVATION_SEAM_DRAFT_2026-04-18.md`, upload review boundary 기준은 `docs/reports/V1_5_UPLOAD_REVIEW_EXECUTOR_BOUNDARY_REVIEW_2026-04-18.md`, audit retention ops 기준은 `docs/reports/V1_5_MUTATION_AUDIT_RETENTION_OPS_DRAFT_2026-04-18.md`, live readiness checklist 기준은 `docs/reports/V1_5_REINDEX_LIVE_READINESS_CHECKLIST_DRAFT_2026-04-19.md`, smoke evidence 기준은 `docs/reports/V1_5_MUTATION_ACTIVATION_SMOKE_EVIDENCE_2026-04-19.md`, checkpoint review 기준은 `docs/reports/V1_5_REINDEX_ACTIVATION_CHECKPOINT_REVIEW_2026-04-19.md`, operator runbook 기준은 `docs/reports/V1_5_REINDEX_ACTIVATION_OPERATOR_RUNBOOK_DRAFT_2026-04-19.md`, live adapter outline 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OUTLINE_DRAFT_2026-04-20.md`, live adapter test plan 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TEST_PLAN_DRAFT_2026-04-20.md`, live adapter success contract 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_SUCCESS_CONTRACT_DRAFT_2026-04-20.md`, opt-in binding seam 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OPT_IN_BINDING_SEAM_DRAFT_2026-04-20.md`, opt-in smoke harness 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OPT_IN_SMOKE_HARNESS_DRAFT_2026-04-20.md`, 테스트 현황/로드맵 요약 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TEST_STATUS_ROADMAP_2026-04-20.md`, executor injection protocol 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_EXECUTOR_INJECTION_PROTOCOL_DRAFT_2026-04-20.md`, binding selection stub 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_BINDING_SELECTION_STUB_DRAFT_2026-04-20.md`, opt-in smoke command 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OPT_IN_SMOKE_COMMAND_DRAFT_2026-04-20.md`, opt-in smoke evidence 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_OPT_IN_SMOKE_EVIDENCE_DRAFT_2026-04-20.md`, concrete executor skeleton 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_CONCRETE_EXECUTOR_SKELETON_DRAFT_2026-04-21.md`, concrete smoke evidence 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_CONCRETE_SMOKE_EVIDENCE_DRAFT_2026-04-21.md`, success promotion 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_DRAFT_2026-04-21.md`, failure taxonomy 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_FAILURE_TAXONOMY_DRAFT_2026-04-21.md`, pre-side-effect executor router implementation 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PRE_SIDE_EFFECT_EXECUTOR_ROUTER_IMPLEMENTATION_DRAFT_2026-04-22.md`, top-level promotion router implementation 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_ROUTER_IMPLEMENTATION_DRAFT_2026-04-22.md`, enablement final checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_FINAL_CHECKPOINT_REVIEW_2026-04-22.md`, guarded live executor implementation 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_IMPLEMENTATION_DRAFT_2026-04-22.md`, guarded live executor smoke command 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_SMOKE_COMMAND_DRAFT_2026-04-22.md`, guarded live executor smoke evidence 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_SMOKE_EVIDENCE_DRAFT_2026-04-22.md`, post-smoke enablement checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_SMOKE_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`, executor error sidecar 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_EXECUTOR_ERROR_SIDECAR_DRAFT_2026-04-22.md`, post-error-sidecar enablement checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_ERROR_SIDECAR_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`, post-executor audit evidence 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_EXECUTOR_AUDIT_EVIDENCE_DRAFT_2026-04-22.md`, post-audit enablement checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_AUDIT_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`, guarded top-level promotion gate 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_TOP_LEVEL_PROMOTION_GATE_DRAFT_2026-04-22.md`, post-promotion enablement checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_PROMOTION_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`, top-level promotion operator runbook update 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_OPERATOR_RUNBOOK_UPDATE_2026-04-22.md`, post-runbook enablement checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_RUNBOOK_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`, rollback drill plan 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ROLLBACK_DRILL_PLAN_DRAFT_2026-04-22.md`, rollback drill harness 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ROLLBACK_DRILL_HARNESS_DRAFT_2026-04-22.md`, rollback drill execution evidence 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ROLLBACK_DRILL_EXECUTION_EVIDENCE_2026-04-22.md`, post-rollback-drill checkpoint 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_ROLLBACK_DRILL_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`, public promotion blocker register 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PUBLIC_PROMOTION_BLOCKER_REGISTER_2026-04-22.md`, local-only closeout 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_LOCAL_ONLY_CLOSEOUT_2026-04-22.md`, post-closeout next-track selection 기준은 `docs/reports/V1_5_POST_CLOSEOUT_NEXT_TRACK_SELECTION_2026-04-22.md`, branch handoff snapshot 기준은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_BRANCH_HANDOFF_SNAPSHOT_2026-04-22.md`, branch publication decision 기준은 `docs/reports/V1_5_BRANCH_PUBLICATION_DECISION_2026-04-22.md`를 따른다. 현재 runtime/middleware는 actor policy source를 읽어 mutation candidate write를 `ADMIN_AUTH_REQUIRED`, `MUTATION_INTENT_REQUIRED`, `PREVIEW_REQUIRED` gate로 차단하고 `preview_contract`, `preview_seed`, draft `apply_envelope`, persisted audit contract, append-only sink receipt를 내부 trace에 남긴다. preview-confirmed apply는 `mutation_apply_guard`가 preview reference/audit receipt/intent summary를 검증한 뒤에도 `MUTATION_APPLY_NOT_ENABLED`로 막아 두고, `services/tool_middleware_service.py`는 blocked apply result 이후 direct tool handler 전 `mutation_apply_guard_pre_side_effect_router` 위치에서 audit receipt를 먼저 만들고 executor router dry-run을 실행하며 `mutation_executor_result` 또는 `mutation_executor_error` sidecar와 `mutation_executor_audit_receipt`, `mutation_top_level_promotion_router` evidence로 future top-level apply success/failure surface mapping을 남긴다. `services/mutation_executor_service.py`는 `reindex`에 대해 operator activation request + durable local audit receipt가 함께 맞을 때 기본 `candidate_stub`, valid explicit binding이 추가되면 `live_binding_stub`, `binding_stage=concrete_executor_skeleton`이 추가되면 side-effect-free `live_result_skeleton`, `binding_stage=guarded_live_executor`가 추가되면 explicit local-only `index_service.reindex()` 호출 seam을 선택하며 `mutation_executor_result` sidecar로 `reindex_summary`, `audit_receipt_ref`, `rollback_hint`를 반환하고 실패 시 `mutation_executor_error` sidecar를 남긴다. `mutation_success_promotion` contract는 current blocked-success sidecar와 future top-level apply success surface의 mapping을 남기며 adapter-specific failure taxonomy helper와 top-level promotion router는 supported executor error code 기준 future top-level failure surface mapping을 고정한다. `services/tool_middleware_service.py`는 guarded executor success/failure 후 `mutation_executor_post_execution` audit record를 append-only sink에 추가하고 pre-executor audit sequence id와 연결한다. Post-audit checkpoint 결론은 default/public top-level promotion `No-Go`, explicit local-only guarded top-level promotion gate implementation planning `Go`다. `executor_binding.top_level_promotion_enabled` 추가 opt-in이 있으면 linked post-executor audit receipt가 있는 guarded path만 top-level success/failure로 승격할 수 있고, 기본 guarded path는 계속 blocked surface를 유지한다. Post-promotion checkpoint 결론은 extra opt-in local-only top-level promotion `Go`, default/public promotion `No-Go`, operator runbook update `Go`다. Operator runbook은 default blocked, activation check, guarded blocked, guarded top-level promotion command와 pre/post audit sequence 확인 절차를 구분한다. Post-runbook checkpoint 결론은 local-only operator surface `Go`, default/public promotion `No-Go`, rollback drill planning `Go`다. Rollback drill plan은 pre-state capture, guarded top-level promotion, audit linkage 확인, rebuild-from-source recovery, post-recovery health/vector check 순서로 고정한다. `scripts/smoke_reindex_rollback_drill.py`는 explicit local env guard, pre-state capture, guarded promotion smoke, rebuild-from-source recovery, post-recovery vector count capture를 구조화해 출력하며, explicit local rollback drill execution은 `ok=true`, audit linkage `6 -> 7`, recovery rebuild `37/37`, post-recovery vector count `37`을 확인했다. `services/index_service.py`는 source metadata를 유지하되 vectorstore ingest 직전 list/dict metadata를 JSON 문자열로 정규화한다. `boundary.live_adapter_outline`는 future live adapter의 target executor, required inputs, expected outputs, success result shape, failure taxonomy, explicit local-only opt-in binding seam, executor injection protocol, opt-in smoke harness separation, rollback awareness를 함께 고정한다. `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TEST_PLAN_DRAFT_2026-04-20.md`는 executor unit, middleware integration, agent runtime, smoke layer별 검증 축과 `future_live_adapter_opt_in_smoke` 분리 원칙을 고정한다. upload review는 rollback/audit/document binding precondition이 정리되기 전까지 `boundary_noop`로 유지한다. `scripts/smoke_agent_runtime.py`는 `v1.5.mutation_activation_smoke.v1` schema로 blocked flow evidence와 `mutation_executor`/`mutation_executor_result`/`mutation_executor_error`/`mutation_executor_audit_receipt`/`audit_sink` summary를 남기고, `--opt-in-live-binding`, `--opt-in-live-binding-stage-concrete`, `--opt-in-live-binding-stage-guarded`, `--opt-in-top-level-promotion`, `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING=1`, `DOC_RAG_MUTATION_SMOKE_LIVE_BINDING_STAGE`, `DOC_RAG_MUTATION_SMOKE_TOP_LEVEL_PROMOTION=1`를 통해 별도 live binding/concrete/guarded/top-level-promotion smoke path를 제공한다. concrete stage summary는 side-effect-free `mutation_success_promotion` 및 `mutation_top_level_promotion_router` evidence를 포함할 수 있고, guarded stage summary는 runtime sidecar가 없으면 실패하며 `actual_runtime_handler_invoked`와 runtime chunks/vectors/scope evidence를 포함한다. `services/tool_audit_sink_service.py`는 default null sink를 유지한 채 explicit local config로만 `local_file_append_only` backend와 stable `sequence_id` receipt를 제공하고, local file receipt/entry에는 `90일` rolling retention과 explicit local-operator prune를 나타내는 nested `ops` contract를 남긴다. 현재 다음 단계는 explicit publication 또는 next-track instruction 대기다.
- 2026-04-21 enablement go/no-go review 결론은 actual execution `No-Go`다. 기준 문서는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_GO_NO_GO_REVIEW_2026-04-21.md`이며, 후속 단계로 `reindex` live adapter pre-execution handoff seam draft를 진행했다.
- 2026-04-21 pre-execution handoff seam draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PRE_EXECUTION_HANDOFF_SEAM_DRAFT_2026-04-21.md`를 기준으로 actual side effect 전 durable audit receipt, mutation executor router, explicit binding, success/failure promotion handoff 순서를 고정한다. 다음 단계는 fake/sandboxed executor smoke seam draft다.
- 2026-04-21 fake executor smoke seam draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_FAKE_EXECUTOR_SMOKE_SEAM_DRAFT_2026-04-21.md`를 기준으로 actual index mutation 없는 success/failure promotion smoke evidence를 고정한다. 다음 단계는 mutation apply executor router dry-run seam draft다.
- 2026-04-22 mutation apply executor router dry-run seam draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_MUTATION_APPLY_ROUTER_DRY_RUN_SEAM_DRAFT_2026-04-22.md`를 기준으로 blocked apply path가 direct `_tool_reindex`/`index_service.reindex`를 호출하지 않고 `mutation_executor_service.execute_mutation_request` dry-run evidence를 남기는 조건을 고정한다. 다음 단계는 execution enablement checkpoint review다.
- 2026-04-22 execution enablement checkpoint review 결론은 actual execution `No-Go`다. 기준 문서는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`이며, 다음 단계는 side effect를 열지 않는 pre-side-effect executor router implementation draft다.
- 2026-04-22 pre-side-effect executor router implementation draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PRE_SIDE_EFFECT_EXECUTOR_ROUTER_IMPLEMENTATION_DRAFT_2026-04-22.md`를 기준으로 valid apply 이후 direct tool handler 전에 audit receipt와 mutation executor router dry-run을 실행하는 runtime path를 고정한다. 다음 단계는 top-level promotion router implementation draft다.
- 2026-04-22 top-level promotion router implementation draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_ROUTER_IMPLEMENTATION_DRAFT_2026-04-22.md`를 기준으로 executor success/failure sidecar를 future top-level apply `result`/`error` surface로 매핑하는 deterministic router evidence를 고정한다. 다음 단계는 execution enablement final checkpoint review다.
- 2026-04-22 execution enablement final checkpoint review 결론은 actual execution `No-Go`, guarded live executor implementation planning `Go`다. 기준 문서는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ENABLEMENT_FINAL_CHECKPOINT_REVIEW_2026-04-22.md`이며, 다음 단계는 actual top-level enablement를 계속 닫은 guarded live executor implementation draft다.
- 2026-04-22 guarded live executor implementation draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_IMPLEMENTATION_DRAFT_2026-04-22.md`를 기준으로 explicit local-only `binding_stage=guarded_live_executor`에서만 `index_service.reindex()` 호출 seam을 열고 current top-level blocked surface를 유지한다.
- 2026-04-22 guarded live executor smoke command draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_SMOKE_COMMAND_DRAFT_2026-04-22.md`를 기준으로 `--opt-in-live-binding-stage-guarded` command surface와 guarded runtime sidecar summary를 고정했다.
- 2026-04-22 guarded live executor smoke evidence draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_LIVE_EXECUTOR_SMOKE_EVIDENCE_DRAFT_2026-04-22.md`를 기준으로 explicit local-only guarded command가 `runtime_chunks=37`, `runtime_vectors=37` sidecar evidence를 남기고 top-level은 `MUTATION_APPLY_NOT_ENABLED` blocked surface를 유지함을 확인했다.
- 2026-04-22 post-smoke enablement checkpoint review는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_SMOKE_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`를 기준으로 guarded local execution evidence는 `Go`, top-level apply success promotion은 `No-Go`, next implementation planning은 `Go`로 판정했다.
- 2026-04-22 executor error sidecar draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_EXECUTOR_ERROR_SIDECAR_DRAFT_2026-04-22.md`를 기준으로 guarded executor failure를 `mutation_executor_error` sidecar와 promotion router failure route evidence로 노출한다.
- 2026-04-22 post-error-sidecar enablement checkpoint review는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_ERROR_SIDECAR_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`를 기준으로 success/failure sidecar readiness는 `Go`, top-level apply success/failure promotion은 `No-Go`, next implementation planning은 `Go`로 판정했다.
- 2026-04-22 post-executor audit evidence draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_EXECUTOR_AUDIT_EVIDENCE_DRAFT_2026-04-22.md`를 기준으로 guarded executor success/failure 후 `mutation_executor_post_execution` audit record와 `mutation_executor_audit_receipt` sidecar를 남긴다. 다음 단계는 post-audit enablement checkpoint review다.
- 2026-04-22 post-audit enablement checkpoint review는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_AUDIT_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`를 기준으로 post-audit readiness `Go`, default/public top-level promotion `No-Go`, explicit local-only guarded promotion gate implementation planning `Go`로 판정했다. 다음 단계는 guarded top-level promotion gate draft다.
- 2026-04-22 guarded top-level promotion gate draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_GUARDED_TOP_LEVEL_PROMOTION_GATE_DRAFT_2026-04-22.md`를 기준으로 extra opt-in이 있는 explicit local-only guarded path만 top-level success/failure로 승격한다. 다음 단계는 post-promotion enablement checkpoint review다.
- 2026-04-22 post-promotion enablement checkpoint review는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_PROMOTION_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`를 기준으로 extra opt-in local-only top-level promotion `Go`, default/public promotion `No-Go`, operator runbook update `Go`로 판정했다. 다음 단계는 top-level promotion operator runbook update다.
- 2026-04-22 top-level promotion operator runbook update는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_OPERATOR_RUNBOOK_UPDATE_2026-04-22.md`를 기준으로 default blocked, activation check, guarded blocked, guarded top-level promotion command와 audit linkage 확인 절차를 operator runbook에 반영했다. 다음 단계는 post-runbook enablement checkpoint review다.
- 2026-04-22 post-runbook enablement checkpoint review는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_RUNBOOK_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`를 기준으로 local-only operator surface `Go`, default/public promotion `No-Go`, rollback drill planning `Go`로 판정했다. 다음 단계는 rollback drill plan draft다.
- 2026-04-22 rollback drill plan draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ROLLBACK_DRILL_PLAN_DRAFT_2026-04-22.md`를 기준으로 pre-state capture, guarded top-level promotion, audit linkage 확인, rebuild-from-source recovery, post-recovery health/vector check 순서를 고정했다. 다음 단계는 rollback drill harness draft다.
- 2026-04-22 rollback drill harness draft는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ROLLBACK_DRILL_HARNESS_DRAFT_2026-04-22.md`를 기준으로 explicit env guard, pre-state capture, guarded promotion smoke, rebuild-from-source recovery, post-recovery vector capture report를 추가했다. 다음 단계는 rollback drill execution evidence다.
- 2026-04-22 rollback drill execution evidence는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_ROLLBACK_DRILL_EXECUTION_EVIDENCE_2026-04-22.md`를 기준으로 explicit local env에서 `ok=true`, audit linkage `6 -> 7`, recovery rebuild `37/37`, post-recovery vector count `37`을 확인했다. 다음 단계는 post-rollback-drill enablement checkpoint review다.
- 2026-04-22 post-rollback-drill enablement checkpoint review는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_POST_ROLLBACK_DRILL_ENABLEMENT_CHECKPOINT_REVIEW_2026-04-22.md`를 기준으로 local-only rollback-drilled operator surface `Go`, extra opt-in local-only top-level promotion `Go`, default/public top-level promotion `No-Go`, upload review live execution `No-Go`로 판정했다. 다음 단계는 public promotion blocker register다.
- 2026-04-22 public promotion blocker register는 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_PUBLIC_PROMOTION_BLOCKER_REGISTER_2026-04-22.md`를 기준으로 product/API contract, authorization, production audit backend, recovery model, concurrency/job lifecycle, upload review boundary, observability/support, regression scope를 default/public blocker로 고정했다. 다음 단계는 local-only closeout이다.
- 2026-04-22 local-only closeout은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_LOCAL_ONLY_CLOSEOUT_2026-04-22.md`를 기준으로 `reindex` explicit local-only operator/test surface `Go`, default/public top-level promotion `No-Go`, upload review live execution `No-Go`를 terminal scope로 고정했다. 다음 단계는 post-closeout next-track selection이다.
- 2026-04-22 post-closeout next-track selection은 `docs/reports/V1_5_POST_CLOSEOUT_NEXT_TRACK_SELECTION_2026-04-22.md`를 기준으로 public blocker implementation 대신 branch handoff snapshot을 선택했다. 다음 단계는 branch handoff snapshot이다.
- 2026-04-22 branch handoff snapshot은 `docs/reports/V1_5_REINDEX_LIVE_ADAPTER_BRANCH_HANDOFF_SNAPSHOT_2026-04-22.md`를 기준으로 branch `codex/loop-034-go-no-go-review`, `main` 대비 `46` commits ahead, `73 files changed`, latest rollback drill `ok=true`, untracked unrelated `.DS_Store`/`TRUNK_RAG_LINKS.md` 상태를 기록했다. 다음 단계는 branch publication decision이다.
- 2026-04-22 branch publication decision은 `docs/reports/V1_5_BRANCH_PUBLICATION_DECISION_2026-04-22.md`를 기준으로 local branch handoff `Go`, automatic remote push/PR `No-Go`, 당시 head `b086055`와 `main` 대비 `47` commits ahead 상태를 snapshot으로 기록했다. 다음 단계는 explicit publication 또는 next-track instruction 대기다.
- 2026-04-27 현행화 시작 시점에는 같은 branch가 head `540128a`, upstream 없음, `main` 대비 `49` commits ahead, `75 files changed`, `12940 insertions`, `41 deletions` 상태였다. 현행화 검증은 `./.venv/bin/python scripts/roadmap_harness.py validate -> ready`, `./.venv/bin/python -m pytest -q -> 239 passed`, `./.venv/bin/python scripts/smoke_agent_runtime.py -> ok=true`이며, 기본 경로의 `reindex` mutation apply는 계속 `MUTATION_APPLY_NOT_ENABLED`로 차단된다.
- 2026-04-27 사용자 지시에 따라 branch `codex/loop-034-go-no-go-review`를 remote에 push하고 draft PR `https://github.com/redsunjin/trunk_rag/pull/5`를 생성했다. 다음 단계는 PR review/merge 후속 또는 다른 MVP/V1/V1.5 track 선택이다.
- 2026-04-27 PR #5는 merge commit `537ab29cb6728aa7f1a27099e974688f7aa4cf37`로 `main`에 병합됐고, 로컬 `main`도 `git pull --ff-only`로 fast-forward 완료됐다. 다음 active는 next-track instruction 대기다.

### 3순위
- 보류 항목 유지
- 내용: GraphRAG 트랙은 잠정 중단 상태로 아카이브만 유지하고, 업로드 관리자 Slice 2는 현재 구현 상태를 유지한다.

### 4순위
- 데스크톱 패키징 실제 착수 재검토
- 내용: embedded Python/설치 전략이 먼저 고정된 경우에만 패키징 재개

## 완료 판정 기준
- `health/reindex/query` 정상 동작
- UI에서 질의/재인덱싱/문서목록 조회/문서보기 가능
- 공통 스타일 적용 유지
- provider 전환 시 치명적 오류 없음
