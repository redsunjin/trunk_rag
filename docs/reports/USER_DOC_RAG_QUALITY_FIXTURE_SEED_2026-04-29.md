# User-Doc RAG Quality Fixture Seed (2026-04-29)

## Scope

- Loop: `LOOP-121 User-doc RAG quality fixture seed`
- Candidate JSONL: `docs/reports/user_doc_quality_fixture_candidates_2026-04-29.jsonl`
- Goal: seed answer-level fixture candidates that evaluate actual operator/user documentation, not only sample-pack demo content.

## Current Corpus Check

- Approved managed docs: none found in `chroma_db/managed_docs/manifest.json`.
- Pending upload request: `ef12174a-c0f9-4325-80d1-35388f73fb84`
- Pending upload content: browser companion smoke capture from `/intro`, only `LOCAL-FIRST RAG`.

Decision:

- Do not promote the pending upload request to a quality fixture. It is too short and was created as smoke evidence, not as a real knowledge document.
- Do not edit `evals/answer_level_eval_fixtures.jsonl` in this loop. The current default RAG corpus still contains sample-pack/demo material and does not index the new operator guide as an approved managed/user document.

## Candidate

### `UDQ-BC-01`

- Source: `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md`
- Source type: project operator document
- Query: `Browser companion에서 graph-lite=hit와 graph-lite=not-reported는 무엇이 다르고, 운영자는 각각 무엇을 확인해야 하나?`
- Required answer signals:
  - `graph-lite=hit`
  - `graph-lite=not-reported`
  - `운영자`
  - `확인`
- Optional expected signals:
  - `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR`
  - `Quality`
  - `snapshot`
  - `debug`
  - `metadata`

## Promotion Gate

`UDQ-BC-01` should move into `evals/answer_level_eval_fixtures.jsonl` only after one of these is true:

1. `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md` is intentionally indexed as an approved managed/user document.
2. A dedicated project-doc collection is introduced and the guide is part of that collection.
3. A real user document with equivalent browser companion operating instructions is approved and active.

Until then, this remains a candidate seed. This prevents the quality gate from expecting answers about documents that the current default RAG corpus cannot retrieve.

## Why This Is Different From Sample-Pack

- Existing `sample-pack-baseline` and `graph-candidate` fixtures evaluate the bundled European science history demo corpus.
- `UDQ-BC-01` evaluates an operator-facing Trunk RAG workflow document.
- The question checks whether RAG can explain system state and operator action, not historical content.
- This is closer to the project destination: local-first RAG over user/operator documents with citations and actionable answers.

## Next Step

`LOOP-122` should use this candidate and the graph-lite smoke evidence to revisit Quality model policy. The key issue is that graph-lite metadata transport can pass while answer text remains weak, so model/prompt quality must be judged separately from retrieval metadata.
