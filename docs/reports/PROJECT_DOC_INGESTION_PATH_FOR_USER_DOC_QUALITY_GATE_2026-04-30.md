# Project-Doc Ingestion Path For User-Doc Quality Gate (2026-04-30)

## Scope

- Loop: `LOOP-123 Project-doc ingestion path for user-doc quality gate`
- Input:
  - `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md`
  - `docs/reports/USER_DOC_RAG_QUALITY_FIXTURE_SEED_2026-04-29.md`
  - `docs/reports/QUALITY_MODEL_DEFAULT_POLICY_REVISIT_2026-04-29.md`
- Boundary: path decision only. No bulk indexing, no default model change, no paid API, and no external service.

## Decision

Use an explicit opt-in `project-doc` collection path for project/operator documents.

Do not use the normal managed-doc workflow for repository-owned operator documents, and do not keep these docs external-only if they are expected to become answer-level quality fixtures.

## Option Review

| option | decision | reason |
| --- | --- | --- |
| Managed-doc workflow | No-Go for repository operator docs | It is designed for user-uploaded runtime content, creates local state under `chroma_db/managed_docs/`, requires admin approval, and can pollute real operator data. |
| External docs only | No-Go for quality gate | The answer-level fixture would ask about content the RAG corpus cannot retrieve, so failures would be invalid. |
| Explicit `project-doc` collection | Go | It keeps product/operator docs separate from sample-pack and user managed docs, is deterministic, and can be opt-in for eval/smoke without changing default runtime behavior. |

## Target Contract

`project-doc` should be treated as a dedicated opt-in collection family:

- Collection key: `project_docs`
- Runtime default: excluded
- Compatibility bundle: excluded
- Source type: `project_operator_doc`
- Initial source candidate: `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md`
- Initial fixture candidate: `UDQ-BC-01`
- Intended use:
  - answer-level quality gate for project/operator documents
  - browser companion and graph-lite operator workflow questions
  - model policy decisions that depend on real user/operator style content

## Required Guardrails

1. `project_docs` must not be added to the default `all` runtime path.
2. `project_docs` must not replace managed-doc workflow for real user uploads.
3. `project_docs` fixtures must explicitly request the project-doc collection or bucket.
4. Project docs must not hide sample-pack/demo boundaries.
5. Promotion from candidate to official fixture must happen only after the project-doc collection is indexable and queryable.

## Implementation Implication

Current seed source loading resolves seed file names from `DATA_DIR`. A project-doc path under `docs/` therefore needs an explicit source loader contract instead of pretending the file is a normal seed markdown file.

Recommended next implementation:

1. Add a small project-doc source manifest or allowlist.
2. Add a source loader that reads allowlisted repo docs by path.
3. Add `project_docs` as an opt-in collection.
4. Add a narrow test that `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md` is included only in `project_docs`.
5. Promote `UDQ-BC-01` to official eval fixture only after the collection is queryable.

## Go/No-Go

- Go: define and implement explicit opt-in `project_docs` collection path.
- No-Go: use managed-doc workflow for repo-owned operator docs.
- No-Go: promote `UDQ-BC-01` before the project-doc collection exists.

## Next Loop

`LOOP-124 Project-doc collection contract skeleton`

Expected output:

- explicit project-doc manifest/allowlist contract
- source-loader skeleton or contract test
- no default runtime behavior change
- `UDQ-BC-01` remains candidate-only until query evidence exists
