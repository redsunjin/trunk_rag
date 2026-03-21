# Release Web MVP Checklist

## 목적

- `trunk_rag`를 "개발자 데모"가 아니라 "배포 가능한 웹 MVP" 기준으로 점검한다.
- 릴리즈 직전 확인 항목을 단일 문서로 고정한다.

## 기본 원칙

- 기본 실행 경로는 `run_doc_rag.bat` 하나로 본다.
- 데스크톱 패키징은 현재 릴리즈 범위에 포함하지 않는다.
- GraphRAG는 아카이브 상태이며 릴리즈 게이트에서 제외한다.

## 릴리즈 전 필수 체크

### 1. 부트스트랩 경로

- [ ] Windows 기준 `.\run_doc_rag.bat` 실행
- [ ] `.env`가 없을 때 자동 생성 확인
- [ ] `.venv`가 없을 때 자동 생성 확인
- [ ] `requirements.txt` 미설치 상태에서 자동 설치 또는 명확한 실패 안내 확인
- [ ] `/intro` 브라우저 오픈 확인

### 2. 첫 실행/복구 가이드

- [ ] `/intro`에서 현재 상태와 다음 행동 안내 확인
- [ ] `vectors=0` 상태에서 Reindex 안내 확인
- [ ] LLM 미준비 상태에서 모델/런타임 확인 안내 확인
- [ ] 질의 실패 응답의 `hint`가 `run_doc_rag.bat`와 `/intro` 기준 복구 경로를 가리키는지 확인

### 3. 핵심 사용자 경로

- [ ] `/intro -> /app` 진입 확인
- [ ] `/intro -> /admin` 진입 확인
- [ ] `/rag-docs` 조회 확인
- [ ] 업로드 요청 생성 확인
- [ ] 관리자 승인/반려 흐름 확인

### 4. 인덱싱/질의 게이트

- [ ] `build_index.py --reset` 또는 `/reindex`로 all-routes 인덱싱 확인
- [ ] `all/eu/fr/ge/it/uk` 컬렉션 벡터 상태 확인
- [ ] `ops-baseline` `3/3 pass` 확인
- [ ] 게이트가 `blocked`면 `Runtime Preflight`와 `Diagnostics`에서 `APP_HEALTH_UNREACHABLE` / `COLLECTIONS_CHECK_FAILED` / `OPS_EVAL_FAILED` 원인 확인
- [ ] 오프라인 재인덱싱이면 `HF_HUB_OFFLINE=1` + 로컬 HuggingFace cache 경로로 복구 가능한지 확인

## 권장 검증 명령

```powershell
.venv\Scripts\python.exe -m pytest -q
.venv\Scripts\python.exe scripts\roadmap_harness.py validate
.venv\Scripts\python.exe scripts\check_ops_baseline_gate.py --llm-provider lmstudio --llm-model qwen3.5-4b-mlx-4bit --llm-base-url http://127.0.0.1:1337/v1
```

## 현재 릴리즈 blocker 판단

- LM Studio/기본 모델 미기동 상태면 질의 게이트를 통과할 수 없다.
- 로컬 임베딩 모델 캐시 또는 `DOC_RAG_EMBEDDING_MODEL` 경로가 없으면 오프라인 환경 첫 실행이 막힐 수 있다.
- `scripts/check_ops_baseline_gate.py`가 `blocked`면 먼저 앱 기동 여부와 diagnostics 코드를 확인한 뒤, 필요한 경우 Reindex 또는 LLM 런타임 복구를 진행한다.
- `VECTORSTORE_EMBEDDING_MISMATCH(409)`가 보이면 현재 임베딩 기준으로 all-routes를 다시 생성하고, 오프라인 환경이면 `HF_HUB_OFFLINE=1` 경로를 우선 사용한다.
- 위 blocker가 남아 있으면 릴리즈 완료로 닫지 않고, `active` 상태를 유지한다.
