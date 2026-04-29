# Project-Doc Collection Contract Skeleton (2026-04-30)

## Scope

- Loop: `LOOP-124 Project-doc collection contract skeleton`
- Input decision: `docs/reports/PROJECT_DOC_INGESTION_PATH_FOR_USER_DOC_QUALITY_GATE_2026-04-30.md`
- Boundary: opt-in contract skeleton only. No default runtime change, no model policy change, no external service.

## Implemented

- Added explicit collection key `project_docs` to `config/collection_manifest.json`.
- Kept `project_docs` out of:
  - `default_runtime_collection_keys`
  - sample-pack `compatibility_bundle.collection_keys`
  - automatic keyword routing keywords
- Added `config/project_doc_manifest.json` as the project/operator-doc allowlist.
- Added `services/project_doc_service.py` to normalize and expose allowlisted project-doc source records.
- Wired `services/index_service.py` so `build_collection_source_records("project_docs")` can include project docs.
- Added tests proving:
  - `project_docs` is explicit-only.
  - default `all` records do not include project docs.
  - `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md` is exposed as a `project_doc` source for `project_docs`.

## Contract

Initial project-doc source:

- collection: `project_docs`
- doc key: `browser_companion_operator_guide`
- path: `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md`
- source type: `project_operator_doc`
- doc type: `operator_guide`

## Guardrails

- Default runtime behavior is unchanged.
- sample-pack compatibility behavior is unchanged.
- `UDQ-BC-01` remains candidate-only until `project_docs` query/index evidence exists.
- The normal managed-doc workflow remains for user uploads and is not used for repository-owned operator docs.

## Verification

- `./.venv/bin/python -m pytest -q tests/test_collection_service.py tests/test_index_service.py` -> `20 passed`
- `env PYTHONPYCACHEPREFIX=/tmp/trunk-rag-pycache ./.venv/bin/python -m py_compile services/project_doc_service.py services/index_service.py core/collection_manifest.py` -> pass

## Next Loop

`LOOP-125 Project-doc query smoke and UDQ candidate promotion gate`

Expected output:

- opt-in reindex/query smoke for `project_docs`
- evidence that `UDQ-BC-01` is retrievable before promotion
- decision whether to promote `UDQ-BC-01` into `evals/answer_level_eval_fixtures.jsonl`
