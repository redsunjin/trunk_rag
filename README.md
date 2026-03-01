# Trunk RAG (Local Server)

폐쇄망/로컬 환경에서 사용하는 경량 RAG 서버입니다.

- 문서: 전처리 완료된 `data/*.md` 입력
- 청킹: `##`, `###`, `####` 헤더 기반 + 문자 분할(기본), 토큰 분할(옵션)
- 벡터스토어: Chroma (로컬 폴더)
- LLM: `openai` / `ollama` / `lmstudio` 선택
- 인터페이스: FastAPI + 브라우저(`http://127.0.0.1:8000`)
- 업로드 워크플로우: 사용자 요청(`pending`) -> 관리자 승인/반려

## Operating Model (현행화)

`trunk_rag`는 "가벼운 RAG 런타임" 역할에 집중합니다.

1. 외부 전처리 단계(별도 프로세스, 클라우드 LLM 포함 가능)
- 원본 소스를 정제해 RAG 정책에 맞는 Markdown으로 변환
- 메타데이터(`source`, `country`, `doc_type`)를 채운 산출물 생성

2. `trunk_rag` 단계(현재 + 다음 단계)
- 현재: 정제된 md를 인덱싱/검색/질의
- 다음 단계(P1): 데이터 등록 시 검증(사용 가능/불가 판정) 기능 추가
- 다음 단계(P1): 분야별 컬렉션 + 단순 라우팅 적용

비목표(현재 단계):
- 원본 수집/크롤링
- 대규모 자동 재작성 파이프라인
- 무거운 rerank/multi-vector 파이프라인 기본 탑재

## Files

- `app_api.py`: 메인 로컬 서버
- `build_index.py`: 초기 인덱스 생성 스크립트
- `common.py`: 공통 유틸리티
- `web/index.html`: 간단 웹 UI
- `web/intro.html`: 인트로/상태 확인 페이지
- `web/admin.html`: 관리자 상태 페이지(MVP)
- `scripts/validate_rag_doc.py`: 등록 전 문서 검증 스크립트
- `scripts/benchmark_token_chunking.py`: char/token 청킹 비교 벤치 스크립트
- `scripts/benchmark_query_e2e.py`: `/query` E2E p95 벤치 스크립트
- `run_doc_rag.bat`: 터미널 명령 없이 서버+브라우저 실행
- `stop_doc_rag.bat`: 실행 중인 로컬 서버 종료
- `.env.example`: 환경변수 템플릿
- `docs/PREPROCESSING_RULES.md`: 전처리 규칙 초안
- `docs/PREPROCESSING_PROMPT_TEMPLATE.md`: 전처리 프롬프트 템플릿
- `docs/PREPROCESSING_METADATA_SCHEMA.json`: 전처리 메타데이터 스키마
- `docs/VECTORSTORE_POLICY.md`: 벡터스토어 운영/용량 정책
- `docs/COLLECTION_ROUTING_POLICY.md`: 분야별 컬렉션/라우팅 정책
- `docs/FUTURE_EXTERNAL_CONSTRAINTS.md`: 외부 제한사항 중 추후 적용 항목

## Quick Start

1. 최초 1회 인덱싱:
```powershell
cd C:\Users\sunji\workspace\doc_rag
C:\Users\sunji\llm_5th\001_chatbot\.venv\Scripts\python.exe build_index.py --reset
```
2. 이후 실행:
```powershell
cd C:\Users\sunji\workspace\doc_rag
.\run_doc_rag.bat
```
3. 브라우저에서 `http://127.0.0.1:8000/intro`가 열리고, `사용자 모드 시작` 버튼으로 `/app` 진입.
   - 관리자 모드는 인증 코드 입력 후 `/admin` 진입
4. 종료:
```powershell
cd C:\Users\sunji\workspace\doc_rag
.\stop_doc_rag.bat
```

수동 실행이 필요하면 기존처럼 `app_api.py` 직접 실행도 가능.

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

`POST /reindex` 응답의 `validation`에는 기계 판독용 필드와 함께
`summary_text`(예: `total=5, usable=5, rejected=0, warnings=0, usable_ratio=100.00%`)가 포함됩니다.

`GET /health` 응답에는 현재 적용 중인 `chunking_mode`(`char` 또는 `token`)와
`query_timeout_seconds`, `max_context_chars`가 포함됩니다.
`POST /reindex` 응답에는 실제 인덱싱에 사용된 `chunking` 설정이 포함됩니다.

예시:

```powershell
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"각 국가별 대표적인 과학적 성과\",\"collection\":\"all\",\"llm_provider\":\"ollama\",\"llm_model\":\"qwen3:4b\",\"llm_base_url\":\"http://localhost:11434\"}"
```

### `/query` 에러 응답 규격

- 성공 응답은 기존과 동일:
```json
{
  "answer": "...",
  "provider": "ollama",
  "model": "qwen3:4b"
}
```

- 실패 응답은 `flat + detail` 호환 포맷:
```json
{
  "code": "LLM_TIMEOUT",
  "message": "LLM 응답 시간이 제한(15초)을 초과했습니다.",
  "hint": "모델 상태를 확인하거나 더 짧은 질문으로 다시 시도하세요.",
  "request_id": "uuid-or-client-id",
  "detail": "LLM 응답 시간이 제한(15초)을 초과했습니다."
}
```

- 타임아웃은 기본 `15초`이며 `DOC_RAG_QUERY_TIMEOUT_SECONDS`로 조정할 수 있습니다.

업로드 요청 생성 예시:

```powershell
curl -X POST http://127.0.0.1:8000/upload-requests `
  -H "Content-Type: application/json" `
  -d "{\"source_name\":\"new_doc.md\",\"collection\":\"fr\",\"country\":\"france\",\"doc_type\":\"country\",\"content\":\"## 제목\\n본문\"}"
```

- 실패 코드 매핑:
  - `INVALID_REQUEST` -> `422`
  - `VECTORSTORE_EMPTY` -> `400`
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

## Preprocessing Contract (정책)

현재 정책:
- `trunk_rag`는 전처리된 md를 입력으로 사용한다.
- 전처리 가이드/규칙은 `docs/PREPROCESSING_RULES.md`를 기준으로 한다.
- 외부 전처리 프롬프트 템플릿은 `docs/PREPROCESSING_PROMPT_TEMPLATE.md`를 사용한다.
- 메타데이터 형식은 `docs/PREPROCESSING_METADATA_SCHEMA.json`을 따른다.

다음 단계(P1) 정책:
- 문서 등록 또는 인덱싱 전 검증을 수행하고 `usable=true/false` 판정을 제공한다.
- 불가(`usable=false`) 문서는 벡터스토어에 반영하지 않는다.

참고:
- 본 정책의 상세 운영 기준은 `docs/FUTURE_EXTERNAL_CONSTRAINTS.md`에 정리한다.

## Environment

`.env.example`를 복사해 `.env` 생성 후 사용.

- OpenAI 사용 시: `OPENAI_API_KEY`
- Ollama 사용 시: `OLLAMA_BASE_URL`
- Ollama 응답 길이 제한(선택): `DOC_RAG_OLLAMA_NUM_PREDICT` (예: `8`, 미설정 시 모델 기본값)
- LM Studio 사용 시: `LMSTUDIO_BASE_URL`, `LMSTUDIO_API_KEY`
- 관리자 모드 인증 코드(선택): `DOC_RAG_ADMIN_CODE` (기본값: `admin1234`)
- 개인 운영 자동 승인(선택): `DOC_RAG_AUTO_APPROVE` (`1/true/on`이면 요청 생성 즉시 승인/인덱싱)
- 질의 타임아웃(선택): `DOC_RAG_QUERY_TIMEOUT_SECONDS` (기본 `15`, 단위 초)
- 컨텍스트 길이 제한(선택): `DOC_RAG_MAX_CONTEXT_CHARS` (미설정 시 제한 없음)
- 청킹 모드(선택): `DOC_RAG_CHUNKING_MODE` (`char` 기본, `token` 옵션)
- 토큰 인코딩(선택): `DOC_RAG_CHUNK_TOKEN_ENCODING` (기본 `cl100k_base`)

## Testing

개발용 테스트 의존성 설치:

```powershell
python -m pip install -r requirements-dev.txt
python -m playwright install chromium
```

실행:

```powershell
pytest -q
```

개별 실행:

```powershell
pytest -q tests/api
pytest -q tests/e2e/test_web_flow_playwright.py -m e2e
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

```powershell
.venv\Scripts\python.exe scripts\benchmark_query_e2e.py `
  --base-url http://127.0.0.1:8000 `
  --llm-provider ollama `
  --llm-model phi3:mini `
  --llm-base-url http://localhost:11434 `
  --rounds 2 `
  --warmup 1 `
  --query-timeout-seconds 120 `
  --output docs\reports\query_e2e_benchmark_2026-02-27.json
```

- 기본 시나리오: `single_all`, `single_fr`, `dual_fr_ge`
- 출력에는 시나리오별 `latency_success_p95_ms`와 `status_counts`가 포함됩니다.
- 느린 로컬 CPU 환경에서는 아래 런타임 설정을 권장:
  - `DOC_RAG_QUERY_TIMEOUT_SECONDS=90`
  - `DOC_RAG_OLLAMA_NUM_PREDICT=8`
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
