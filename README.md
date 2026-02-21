# doc_rag (Local Server)

폐쇄망/로컬 환경에서 사용하는 경량 RAG 서버입니다.

- 문서: `data/*.md` (고정 5개 파일)
- 청킹: `##`, `###`, `####` 헤더 기반 + 문자 분할
- 벡터스토어: Chroma (로컬 폴더)
- LLM: `openai` / `ollama` / `lmstudio` 선택
- 인터페이스: FastAPI + 브라우저(`http://127.0.0.1:8000`)

## Files

- `app_api.py`: 메인 로컬 서버
- `build_index.py`: 초기 인덱스 생성 스크립트
- `common.py`: 공통 유틸리티
- `web/index.html`: 간단 웹 UI
- `web/intro.html`: 인트로/상태 확인 페이지
- `run_doc_rag.bat`: 터미널 명령 없이 서버+브라우저 실행
- `.env.example`: 환경변수 템플릿

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
3. 브라우저에서 `http://127.0.0.1:8000/intro`가 열리고, `서비스 시작` 버튼으로 `/app` 진입.

수동 실행이 필요하면 기존처럼 `app_api.py` 직접 실행도 가능.

## API

- `GET /health`: 서버/벡터 상태 확인
- `POST /reindex`: 문서 재인덱싱
- `POST /query`: 질의
- `GET /rag-docs`: RAG 대상 문서 목록
- `GET /rag-docs/{doc_name}`: 문서 원문(md) 조회

예시:

```powershell
curl http://127.0.0.1:8000/health

curl -X POST http://127.0.0.1:8000/query `
  -H "Content-Type: application/json" `
  -d "{\"query\":\"각 국가별 대표적인 과학적 성과\",\"llm_provider\":\"ollama\",\"llm_model\":\"qwen3:4b\",\"llm_base_url\":\"http://localhost:11434\"}"
```

## Environment

`.env.example`를 복사해 `.env` 생성 후 사용.

- OpenAI 사용 시: `OPENAI_API_KEY`
- Ollama 사용 시: `OLLAMA_BASE_URL`
- LM Studio 사용 시: `LMSTUDIO_BASE_URL`, `LMSTUDIO_API_KEY`
