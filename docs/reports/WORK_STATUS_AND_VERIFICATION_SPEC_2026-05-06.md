# Work Status and Verification Spec

- Loop: `LOOP-129 Work status and verification spec`
- Date: `2026-05-06`
- Baseline: `main` / `origin/main` at `d7a12bc LOOP-127 add user-doc quality gate command`
- Scope: summarize the completed project-doc/user-doc quality gate track and define the repeatable checks that prove it is working.

## Current State At Closeout

- Producing loop: `LOOP-129 Work status and verification spec`
- Next active item after closeout: `LOOP-130 Await next-track after work status spec`
- Previous active item: `LOOP-128 Await next-track after user-doc quality gate`
- `LOOP-128` is closed because the next track was explicitly selected as this specification pass.
- Expected queue status after this loop: `active=1`, `pending=0`, `blocked=1`, `done=127`, `archived=1`
- Remaining blocked track: `LOOP-005 Desktop packaging restart`, blocked until `embedded Python` vs `separate install` strategy is decided.
- Local untracked files observed during closeout: `.DS_Store`, `TRUNK_RAG_LINKS.md`. They are not part of this spec.

## Completed Track Summary

### LOOP-123 Project-Doc Ingestion Path

- Decision: explicit opt-in `project_docs` collection path is Go.
- Guardrail: `project_docs` must not enter the default `all` runtime path or sample-pack compatibility bundle.
- Report: `docs/reports/PROJECT_DOC_INGESTION_PATH_FOR_USER_DOC_QUALITY_GATE_2026-04-30.md`

### LOOP-124 Project-Doc Collection Contract

- Added explicit-only `project_docs` collection contract.
- Key files:
  - `config/project_doc_manifest.json`
  - `services/project_doc_service.py`
  - `core/collection_manifest.py`
  - `services/index_service.py`
- Report: `docs/reports/PROJECT_DOC_COLLECTION_CONTRACT_SKELETON_2026-04-30.md`

### LOOP-125 Project-Doc Query Smoke

- Reindex smoke for `project_docs`: `docs=1/1`, `chunks=10`, `vectors=10`, usable ratio `100.00%`.
- Query smoke used explicit `project_docs` and returned supported citations from `BROWSER_COMPANION_OPERATOR_GUIDE.md`.
- `UDQ-BC-01` remained candidate-only at this step because the generated answer still contained a false not-found answer body.
- Report: `docs/reports/PROJECT_DOC_QUERY_SMOKE_AND_UDQ_PROMOTION_GATE_2026-04-30.md`

### LOOP-126 Supported-Context False Not-Found Guard

- `/query` now computes source/citation/support on successful responses even when debug is off.
- If supported or limited context exists but the generated answer ends as not-found, the answer guard returns evidence lines from retrieved context.
- Guard marker: `invoke.answer_guard.reason=supported_context_false_not_found`
- `UDQ-BC-01` was promoted into the opt-in user-doc fixture file, not the default baseline fixture.
- Key files:
  - `services/query_service.py`
  - `api/routes_query.py`
  - `evals/user_doc_answer_level_eval_fixtures.jsonl`
- Reports:
  - `docs/reports/SUPPORTED_CONTEXT_FALSE_NOT_FOUND_REMEDIATION_2026-04-30.md`
  - `docs/reports/USER_DOC_QUERY_ANSWER_EVAL_2026-04-30_LOOP126.md`

### LOOP-127 User-Doc Quality Gate Operator Command

- Added `scripts/check_user_doc_quality_gate.py`.
- Gate target:
  - eval file: `evals/user_doc_answer_level_eval_fixtures.jsonl`
  - bucket: `user-doc-candidate`
  - case: `UDQ-BC-01`
  - required collection: `project_docs`
- Boundary:
  - default release gate remains `scripts/check_ops_baseline_gate.py` with `generic-baseline`
  - `project_docs` is not added to default runtime collections
  - user-doc fixtures are not promoted into `evals/answer_level_eval_fixtures.jsonl`
  - model defaults are not changed
- Recovery diagnostic: `PROJECT_DOCS_REINDEX_REQUIRED` includes a `project_docs` reindex hint.
- Report: `docs/reports/USER_DOC_QUALITY_GATE_OPERATOR_COMMAND_2026-04-30.md`

## Verification Matrix

### Repository and Harness

```bash
git status -sb
./.venv/bin/python scripts/roadmap_harness.py status
./.venv/bin/python scripts/roadmap_harness.py validate
```

Expected:

- `main` and `origin/main` are aligned after publish.
- `tracked_dirty=False`.
- Harness status is `ready`.
- Exactly one top-level `active` item exists.

### Target Regression

```bash
./.venv/bin/python -m pytest -q \
  tests/test_check_user_doc_quality_gate.py \
  tests/test_user_doc_eval_fixtures.py \
  tests/test_documentation_boundaries.py
```

Expected:

- `8 passed`

### App and Runtime Boundary

Ollama and the Trunk RAG app server are separate services.

```bash
curl -s http://localhost:11434/api/tags
curl -s http://127.0.0.1:8000/health
```

Expected:

- Ollama returns installed model tags including `gemma4:e4b`.
- App `/health` returns `status=ok`, `release_web_status=ready`, `vectors>0`, and runtime profile status `verified`.

### User-Doc Quality Gate

Start the app server first:

```bash
./.venv/bin/python app_api.py
```

Then run:

```bash
./.venv/bin/python scripts/check_user_doc_quality_gate.py \
  --llm-provider ollama \
  --llm-model gemma4:e4b \
  --llm-base-url http://localhost:11434 \
  --query-timeout-seconds 60 \
  --json
```

Expected:

- exit code `0`
- `ready=true`
- `collections.items[project_docs].vectors=10`
- `eval.summary.cases=1`
- `eval.summary.passed=1`
- `eval.summary.support_pass_rate=1.0`
- `eval.summary.source_route_pass_rate=1.0`
- `eval.summary.avg_weighted_score=1.0`

Latest observed live smoke:

- Time: `2026-05-05 02:14 KST`
- Result: `ready=true`, `UDQ-BC-01 1/1 passed`, `support_pass_rate=1.0`, `source_route_pass_rate=1.0`, `avg_weighted_score=1.0`
- Note: the earlier `APP_HEALTH_UNREACHABLE` was caused by the Trunk RAG app server being stopped, not by Ollama. Ollama was reachable at `http://localhost:11434`.

## Operational Interpretation

- The completed track proves that project/operator documentation can be evaluated through an explicit `project_docs` path without changing the default release gate.
- The default user path remains the web MVP route with the `all` collection and `generic-baseline` release gate.
- User-doc evaluation remains opt-in until more real user/operator documents are available and promoted through a separate fixture decision.
- Desktop packaging remains blocked and is not part of the completed user-doc quality gate track.

## Next Track Candidates

1. `User-doc quality gate live evidence artifact`
   - Persist the live gate output with `--output-json docs/reports/user_doc_quality_gate_latest.json` and `--output-report docs/reports/USER_DOC_QUALITY_GATE_LATEST.md`.
2. `User-doc fixture expansion`
   - Add one or two more real project/operator document questions before promoting user-doc quality beyond `UDQ-BC-01`.
3. `Desktop packaging strategy decision`
   - Unblock `LOOP-005` only after deciding embedded Python vs separate install.
