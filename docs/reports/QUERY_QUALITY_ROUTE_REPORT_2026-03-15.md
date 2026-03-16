# Query Quality and Routing Report (2026-03-15)

## 목적
- `char` 기본 모드와 `token_800_120` 후보를 동일한 질의로 비교해 품질 차이가 있는지 확인한다.
- 자동 컬렉션 라우팅이 교차 국가 비교 질의에서 실제로 도움이 되는지 확인한다.

## 측정 프로파일
- 서버: `app_api:app`
- LLM: `ollama` + `llama3.1:8b`
- LLM base URL: `http://127.0.0.1:11434`
- query timeout: `90s`
- `DOC_RAG_OLLAMA_NUM_PREDICT=128`
- `DOC_RAG_MAX_CONTEXT_CHARS=1500`
- embedding model: 로컬 경로의 `minishlab/potion-base-4M`
- embedding device: `cpu`
- 비교 모드:
  - `char`
  - `token_800_120`

참고:
- 이번 품질 비교도 공식 기본 스택(`BAAI/bge-m3`, `qwen3:4b`)이 아니라 로컬에서 즉시 실행 가능한 프로파일 기준이다.
- 목적은 "기본값을 뒤집을 정도의 품질 차이가 있는지"를 빠르게 판단하는 것이다.

## 샘플 질의
1. `프랑스의 에콜 폴리테크니크가 어떤 역할을 했는지 요약해줘`
2. `프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학은 과학 인재 양성에서 어떤 역할을 했는지 비교해줘`
3. 2번 질의에 `collection=all`을 명시한 비교

## 결과 요약

| case | char route | token route | 관찰 |
| --- | --- | --- | --- |
| `fr_auto` | `rag_science_history_fr` | `rag_science_history_fr` | 두 모드 모두 동일한 요약 응답 |
| `compare_auto` | `rag_science_history_fr,rag_science_history_ge` | `rag_science_history_fr,rag_science_history_ge` | 두 모드 모두 비교 응답 가능 |
| `compare_all` | `w2_007_header_rag` | `w2_007_header_rag` | 두 모드 모두 `제공된 문서에서 확인되지 않습니다.` |

## 해석
1. 샘플 질의 기준으로 `char`와 `token_800_120`의 응답 품질 차이는 확인되지 않았다.
2. 품질 차이를 만든 핵심 요소는 청킹 모드가 아니라 자동 라우팅이었다.
3. 교차 국가 비교 질의에서 `collection=all`은 같은 프로파일에서도 충분한 답변을 주지 못했다.
4. 자동 다중 라우팅(`fr,ge`)은 같은 질의에서 비교 가능한 답변을 생성했다.

## 결론
- 운영 기본 청킹 모드는 `char`를 유지한다.
- 자동 라우팅 기본값은 다음 순서를 따른다:
  1. 명시 `collection`/`collections`
  2. 키워드 2개 이하 자동 매칭 시 해당 컬렉션 사용
  3. 키워드 없음 또는 과다 매칭 시 `all` fallback
- 교차 국가 비교 질문의 기본 경로는 `all` 고정이 아니라 자동 다중 라우팅이다.
- `token_800_120`은 유지 가능한 후보지만, 이번 품질 비교만으로 기본값을 바꿀 근거는 부족하다.
