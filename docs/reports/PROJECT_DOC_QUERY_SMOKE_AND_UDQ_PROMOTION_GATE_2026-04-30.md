# Project-Doc Query Smoke And UDQ Promotion Gate (2026-04-30)

## Scope

- Loop: `LOOP-125 Project-doc query smoke and UDQ candidate promotion gate`
- Input:
  - `docs/reports/PROJECT_DOC_COLLECTION_CONTRACT_SKELETON_2026-04-30.md`
  - `docs/reports/USER_DOC_RAG_QUALITY_FIXTURE_SEED_2026-04-29.md`
- Boundary: opt-in project-doc smoke and promotion decision only. No default runtime change, no model default change, no fixture promotion.

## Reindex Smoke

Command:

```bash
./.venv/bin/python -c "from services import index_service; import json; result=index_service.reindex_single_collection(reset=False, collection_key='project_docs'); print(json.dumps(result, ensure_ascii=False, indent=2))"
```

Result:

- collection: `rag_project_docs`
- collection_key: `project_docs`
- docs: `1/1`
- chunks: `10`
- vectors: `10`
- validation: `total=1, usable=1, rejected=0, warnings=0, usable_ratio=100.00%`
- persist_dir: `chroma_db`

`reset=False` was used to avoid deleting any existing local collection state.

## Query Smoke

Server:

```bash
./.venv/bin/python -m uvicorn app_api:app --host 127.0.0.1 --port 8015
```

Query:

```bash
curl -s http://127.0.0.1:8015/query \
  -H 'Content-Type: application/json' \
  -d '{"query":"Browser companion에서 graph-lite=hit와 graph-lite=not-reported는 무엇이 다르고, 운영자는 각각 무엇을 확인해야 하나?","collection":"project_docs","quality_mode":"balanced","quality_stage":"balanced","timeout_seconds":60,"debug":true}'
```

Result:

- request_id: `c12fce7d-dfa8-493f-b3b5-40131542ac1f`
- collections: `project_docs`
- route_reason: `explicit`
- support_level: `supported`
- citations:
  - `BROWSER_COMPANION_OPERATOR_GUIDE.md > Graph-Lite Quality Smoke`
  - `BROWSER_COMPANION_OPERATOR_GUIDE.md > Graph-Lite Status Meanings`
- answer text: `제공된 문서에서 확인되지 않습니다.`

The loop-specific server on `:8015` was stopped after the smoke, and a final `/health` check returned connection failure.

## Promotion Decision

`UDQ-BC-01` remains candidate-only.

Reason:

- Retrieval and citation routing work for `project_docs`.
- The answer body failed the expected answer quality even though `support_level=supported` and relevant citations were present.
- Promoting this candidate now would create a failing official fixture without first addressing the supported-context false "not found" behavior.

## Next Step

`LOOP-126 Supported-context false-not-found remediation`

Goal:

- Reduce or gate responses where retrieval/citations/support are present but the generated answer still says the information is unavailable.
- Re-run `UDQ-BC-01` after remediation.
- Promote the fixture only after the answer body includes the required signals.
