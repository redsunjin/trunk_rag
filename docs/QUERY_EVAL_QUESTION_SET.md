# Query Eval Question Set (2026-04-05)

## 목적
- 본체 기본 게이트(`generic-baseline`)와 샘플팩 호환 평가(`sample-pack-baseline`)를 분리한다.
- GraphRAG 후보 질문은 별도 `graph-candidate` 버킷으로 유지한다.

## 사용 원칙
- `generic-baseline`
  - 본체 기본 `/query` 품질 게이트
  - 범용 query profile 기준으로 통과해야 하는 질문
- `sample-pack-baseline`
  - 유럽 과학사 샘플팩 전용 질문
  - `sample_pack` query profile을 켰을 때의 호환성 평가
- `graph-candidate`
  - 여러 인물/기관/국가/사건의 관계 연결이 핵심이라 GraphRAG 후보로 보는 질문

## 질문셋

| id | bucket | 대상 컬렉션 | relation shape | 질문 |
| --- | --- | --- | --- | --- |
| GQ-01 | sample-pack-baseline | `fr` | institution -> role | 에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘. |
| GQ-03 | sample-pack-baseline | `uk` | scientist -> social status | 뉴턴의 국장이 영국 사회에서 무엇을 상징했는지 설명해줘. |
| GQ-05 | sample-pack-baseline | `fr,ge` | country -> institution comparison | 프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학이 인재 양성에서 어떻게 다른지 비교해줘. |
| GQ-09 | graph-candidate | `uk,ge,fr` | scientist -> event -> intellectual diffusion | 뉴턴의 국장, 볼테르의 충격, 프랑스/독일 계몽주의 확산이 어떤 연쇄로 이어졌는지 설명해줘. |
| GQ-12 | graph-candidate | `ge` | lab -> people -> society -> industry | 마그누스 실험실에서 시작된 네트워크가 헬름홀츠, 지멘스, 독일 물리학회, 산업화로 어떻게 이어졌는지 설명해줘. |
| GQ-15 | graph-candidate | `fr,ge,uk,it` | country -> institution -> scientist network | 에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학을 한 관계망으로 놓고 각자의 역할을 설명해줘. |
| GQ-19 | generic-baseline | `fr` | institution -> function summary | 문서 기준으로 에콜 폴리테크니크가 어떤 방식으로 과학 인재를 길렀는지 요약해줘. |
| GQ-20 | generic-baseline | `uk` | event -> social meaning | 문서 기준으로 뉴턴의 국장이 당시 영국에서 과학의 위상을 어떻게 보여줬는지 설명해줘. |
| GQ-21 | generic-baseline | `fr,ge` | institution -> training comparison | 문서 기준으로 에콜 폴리테크니크와 훔볼트 대학의 인재 육성 방식 차이를 정리해줘. |

## 분리 기준

### 본체 기본 게이트(`generic-baseline`)
- 기본 `generic` query profile 그대로 통과해야 한다.
- 특정 샘플팩 문구 보정 없이도 답변 품질을 유지해야 한다.
- 운영 게이트와 `/ops-baseline/latest`는 이 버킷만 사용한다.

### 샘플팩 호환성(`sample-pack-baseline`)
- 샘플팩 전용 프롬프트와 후처리 규칙을 켰을 때의 호환성을 본다.
- 기본 제품 게이트가 아니라 샘플팩 유지보수용 평가다.

### Graph 후보(`graph-candidate`)
- 3개 이상 국가/기관/인물 연결
- 사건 -> 인물 -> 제도 -> 산업화처럼 관계 사슬이 핵심

## 다음 단계
1. `generic-baseline` 결과를 운영 게이트 기준으로 유지한다.
2. `sample-pack-baseline`은 샘플팩 회귀나 데모 점검이 필요할 때만 별도 실행한다.
3. `graph-candidate`는 archive/실험 문맥으로만 유지한다.
