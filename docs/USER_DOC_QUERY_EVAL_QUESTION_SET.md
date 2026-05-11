# User-Doc Query Eval Question Set

이 질문셋은 bundled sample-pack이 아니라 실제 운영자/사용자 문서 RAG 품질을 검증한다.

| id | bucket | collections | relation_shape | query |
| --- | --- | --- | --- | --- |
| UDQ-BC-01 | user-doc-candidate | `project_docs` | operator status -> action comparison | Browser companion에서 graph-lite=hit와 graph-lite=not-reported는 무엇이 다르고, 운영자는 각각 무엇을 확인해야 하나? |
| UDQ-BC-02 | user-doc-candidate | `project_docs` | normal operation -> mode selection | Browser companion을 로컬에서 정상 사용하려면 side panel에서 어떤 상태를 확인하고, Balanced와 Quality 모드는 각각 언제 써야 하나? |
| UDQ-BC-03 | user-doc-candidate | `project_docs` | upload draft -> admin workflow guardrail | Browser companion의 Upload Draft for Review는 문서를 어떻게 처리하며, smoke 실행과 pending 요청 정리에서 운영자가 지켜야 할 제한은 무엇인가? |
