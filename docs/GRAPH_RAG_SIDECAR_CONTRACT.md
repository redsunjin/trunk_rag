# GraphRAG Sidecar Contract (Archive, 2026-03-17)

> 이 문서는 GraphRAG 잠정 중단 이후 참고용 아카이브다.
> 현재 본체 기준 문맥은 `docs/GRAPH_RAG_ARCHIVE_INDEX.md`에서만 연결하고, 운영/릴리즈 판단에는 직접 사용하지 않는다.
> 2026-04-28 graph-lite PoC는 `docs/GRAPH_LITE_RELATION_SIDECAR_CONTRACT.md`를 기준으로 하며, 이 archive 계약의 Neo4j/full GraphRAG 운영안을 재개하지 않는다.

## 목적
- GraphRAG를 본체 직접 통합이 아니라 sidecar로 붙일 때의 최소 계약을 고정한다.
- 실제 PoC 구현이 어디까지면 충분한지 범위를 명확히 한다.

## 전제
- 기본 `/query`는 계속 기존 Vector RAG가 담당한다.
- GraphRAG는 `graph-candidate` 질문군에만 선택적으로 적용한다.
- 그래프 저장소 기본안은 self-managed Neo4j다.
- AuraDB는 기본안이 아니다.

## 최소 적재 파이프라인

| 단계 | 입력 | 출력 | 비고 |
| --- | --- | --- | --- |
| 1. source resolve | `data/*.md` + managed active docs | 승인된 markdown 집합 | seed + managed active 버전 기준 |
| 2. section split | markdown | section/unit JSONL | `##/###/####` 기준 헤더 단위 유지 |
| 3. entity/relation extract | section/unit JSONL | entity JSONL + relation JSONL | PoC는 규칙+LLM 혼합 추출 허용 |
| 4. graph load | entity/relation JSONL | Neo4j graph | 로컬 단일 인스턴스 기준 |
| 5. graph snapshot metadata | ingest run result | stats JSON | entity 수, relation 수, source coverage 기록 |

### 파이프라인 최소 산출물
- `entities.jsonl`
- `relations.jsonl`
- `ingest_stats.json`

### 실패 정책
- 추출 실패 section은 전체 ingest를 중단하지 않고 warning으로 남긴다.
- graph ingest 실패는 sidecar만 degraded 상태로 두고 본체 `/query`는 유지한다.

## 런타임 계약

### 호출 위치
- 본체 FastAPI는 아래 조건 중 하나일 때만 sidecar를 호출한다.
  1. 사용자가 명시적으로 고급 추론 모드를 요청
  2. 질문이 `docs/GRAPH_RAG_QUESTION_SET.md`의 `graph-candidate` 특성과 맞음

### 요청 API
- endpoint: `POST /query-advanced`

요청 예:

```json
{
  "query": "뉴턴의 국장, 볼테르의 충격, 프랑스/독일 계몽주의 확산이 어떤 연쇄로 이어졌는지 설명해줘",
  "collections": ["uk", "ge", "fr"],
  "request_id": "uuid",
  "mode": "graph_hybrid",
  "fallback_allowed": true,
  "max_hops": 3
}
```

필드:
- `query`: 사용자 질문
- `collections`: 본체 라우터가 먼저 좁힌 컬렉션 후보
- `request_id`: 본체 요청 ID 재사용
- `mode`: PoC 기본값은 `graph_hybrid`
- `fallback_allowed`: sidecar 실패 시 본체 vector fallback 허용 여부
- `max_hops`: PoC 기본 `2~3`

### 응답 API

성공 예:

```json
{
  "answer": "...",
  "mode": "graph_hybrid",
  "used_collections": ["uk", "ge", "fr"],
  "entities": ["Newton", "Voltaire", "Leibniz"],
  "relations": [
    "Newton funeral -> Voltaire shock",
    "Voltaire influence -> French/German enlightenment"
  ],
  "fallback_used": false,
  "request_id": "uuid"
}
```

fallback 예:

```json
{
  "answer": "...",
  "mode": "vector_fallback",
  "used_collections": ["uk", "ge"],
  "entities": [],
  "relations": [],
  "fallback_used": true,
  "fallback_reason": "SIDECAR_TIMEOUT",
  "request_id": "uuid"
}
```

## 본체 라우터 규칙
1. 기본 경로는 현재 `/query`
2. 질문이 `ops-baseline`이면 sidecar 호출 금지
3. 질문이 `graph-candidate`면:
   - 최대 3개 컬렉션 후보까지 sidecar에 전달 가능
   - sidecar 실패 시 현재 Vector RAG로 즉시 fallback
4. 본체는 sidecar 결과를 강제하지 않고, timeout/오류/빈 결과 시 fallback 결정권을 가진다

## fallback 규칙
- sidecar timeout
- Neo4j 연결 실패
- graph hit 없음
- relation confidence 임계 미달

위 경우:
- 본체는 현재 `/query`와 동일한 vector 경로로 재시도한다.
- 사용자에게는 "고급 관계 추론 unavailable, 기본 답변으로 fallback" 정도의 정보만 노출한다.
- 운영 로그에는 `request_id`, `fallback_reason`, `collections`, `elapsed_ms`를 남긴다.

## 비교표

| 항목 | 현재 Vector RAG | GraphRAG sidecar PoC 목표 |
| --- | --- | --- |
| 기본 질의 속도 | 빠르고 단순 | 기본 경로를 건드리지 않음 |
| 1~2개 컬렉션 비교 | 자동 다중 라우팅으로 일부 대응 | sidecar 대상 아님 |
| 3개 이상 관계 연결 | 구조적으로 약함 | 관계 경로 복원 시도 |
| 장애 격리 | 본체 단일 경로 | sidecar 장애 시 vector fallback |
| 운영 복잡도 | 낮음 | Neo4j + 적재 파이프라인 추가 |
| 폐쇄망 적합성 | 높음 | self-managed Neo4j 전제 시 유지 가능 |

## 이번 계약의 완료 기준
- 입력 markdown -> entity/relation -> Neo4j 적재 흐름이 문서로 정의돼 있다.
- `query router -> graph/vector hybrid retrieval -> fallback` 계약이 문서로 정의돼 있다.
- 정확도/지연/운영 복잡도 비교표가 존재한다.

## 아직 미완료인 것
- 실제 sidecar 구현
- accuracy 개선 실측
- latency 측정
- Go/No-Go 판단
