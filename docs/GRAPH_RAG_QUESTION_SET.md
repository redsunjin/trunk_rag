# GraphRAG Question Set (2026-03-17)

## 목적
- 관계형/다중 홉 질문 15~20개를 고정한다.
- 현재 Vector RAG 기본 경로로 볼 질문과, GraphRAG 후보로 분리해 평가 기준을 만든다.

## 사용 원칙
- `ops-baseline`
  - 현재 Vector RAG + 자동 다중 라우팅으로도 다뤄야 하는 운영 질문
- `graph-candidate`
  - 여러 인물/기관/국가/사건의 관계 연결이 핵심이라 GraphRAG 후보로 보는 질문

## 질문셋

| id | bucket | 대상 컬렉션 | relation shape | 질문 |
| --- | --- | --- | --- | --- |
| GQ-01 | ops-baseline | `fr` | institution -> role | 에콜 폴리테크니크가 프랑스 과학 인재 양성에서 맡은 역할을 요약해줘. |
| GQ-02 | ops-baseline | `ge` | institution -> model | 훔볼트 대학이 독일 과학 체계화에서 어떤 의미를 가졌는지 설명해줘. |
| GQ-03 | ops-baseline | `uk` | scientist -> social status | 뉴턴의 국장이 영국 사회에서 무엇을 상징했는지 설명해줘. |
| GQ-04 | ops-baseline | `it` | institution -> autonomy | 파도바 대학이 왜 학문의 자유와 저항 정신의 상징으로 다뤄지는지 설명해줘. |
| GQ-05 | ops-baseline | `fr,ge` | country -> institution comparison | 프랑스의 에콜 폴리테크니크와 독일의 훔볼트 대학이 인재 양성에서 어떻게 다른지 비교해줘. |
| GQ-06 | ops-baseline | `uk,ge` | institution -> institution comparison | 영국 왕립학회와 독일 물리학회가 각각 어떤 방식으로 과학 제도화를 이끌었는지 비교해줘. |
| GQ-07 | ops-baseline | `uk,it` | institution -> culture comparison | 옥스퍼드/케임브리지 네트워크와 이탈리아 대학 자치 전통을 비교해줘. |
| GQ-08 | ops-baseline | `eu` | country -> summary | 유럽 주요 국가들이 과학자를 예우한 방식의 공통점과 차이를 요약해줘. |
| GQ-09 | graph-candidate | `uk,ge,fr` | scientist -> event -> intellectual diffusion | 뉴턴의 국장, 볼테르의 충격, 프랑스/독일 계몽주의 확산이 어떤 연쇄로 이어졌는지 설명해줘. |
| GQ-10 | graph-candidate | `uk,ge` | scientist -> rivalry -> national prestige | 뉴턴과 라이프니츠의 미적분 논쟁이 양국 과학 자존심 경쟁으로 어떻게 번졌는지 설명해줘. |
| GQ-11 | graph-candidate | `it,fr,uk` | patron -> scientist -> model transfer | 메디치 가문의 갈릴레오 후원이 이후 프랑스와 영국의 과학 후원 모델에 어떤 표준을 남겼는지 설명해줘. |
| GQ-12 | graph-candidate | `ge` | lab -> people -> society -> industry | 마그누스 실험실에서 시작된 네트워크가 헬름홀츠, 지멘스, 독일 물리학회, 산업화로 어떻게 이어졌는지 설명해줘. |
| GQ-13 | graph-candidate | `it` | institution -> migration -> scientific output | 볼로냐와 파도바의 대학 자치가 학자 이동과 연구 성과에 어떤 영향을 주었는지 설명해줘. |
| GQ-14 | graph-candidate | `fr,ge,uk` | war/crisis -> institution design | 프랑스 혁명, 나폴레옹 전쟁 이후 독일 재건, 런던 대화재가 각국 과학 제도 설계에 어떤 영향을 줬는지 연결해줘. |
| GQ-15 | graph-candidate | `fr,ge,uk,it` | country -> institution -> scientist network | 에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학을 한 관계망으로 놓고 각자의 역할을 설명해줘. |
| GQ-16 | graph-candidate | `ge,uk` | city -> institution -> war -> recovery | 괴팅겐의 과학 자산이 전쟁 중 보호되고 전후 인재 이동과 막스 플랑크 연구소 재건으로 이어진 흐름을 설명해줘. |
| GQ-17 | graph-candidate | `fr,ge,uk` | institution model -> international diffusion | 에콜 폴리테크니크, 훔볼트 모델, 왕립학회가 후대 다른 기관 모델로 어떻게 확산됐는지 설명해줘. |
| GQ-18 | graph-candidate | `it,fr,ge,uk` | person -> institution -> symbol -> policy | 갈릴레오, 뉴턴, 라이프니츠, 몽주, 헬름홀츠를 국가/제도/상징의 연결선으로 묶어 설명해줘. |

## 분리 기준

### 운영 질문(`ops-baseline`)
- 단일 국가 또는 최대 2개 국가 비교
- 문서 내부에 이미 요약된 제도/인물/기관 설명이 중심
- 현재 자동 다중 라우팅과 상위 k 검색으로도 답을 만들 수 있어야 함

### Graph 후보 질문(`graph-candidate`)
- 3개 이상 국가/기관/인물 연결
- 사건 -> 인물 -> 제도 -> 산업화처럼 관계 사슬이 핵심
- 답이 "같은 문장 근처의 요약"이 아니라 여러 문서의 연결 구조 복원이 필요함

## 다음 단계
1. 위 질문셋을 기준으로 current Vector RAG의 실패/성공 사례를 문서화한다.
2. 실패가 반복되는 질문만 GraphRAG sidecar PoC 후보로 남긴다.
3. `ops-baseline`은 GraphRAG가 아니라 기존 `/query` 품질 기준으로 유지한다.
