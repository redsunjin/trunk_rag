# Supported-Context False Not-Found Remediation (2026-04-30)

## Scope

- Loop: `LOOP-126 Supported-context false-not-found remediation`
- Trigger: `UDQ-BC-01` returned `support_level=supported` and relevant citations, but the answer body was `제공된 문서에서 확인되지 않습니다.`
- Boundary: no model default change, no default runtime collection change, no external API.

## Change

- Added an answer guard in `/query`:
  - classify support/citations for every successful query, not only debug responses
  - when `support_level` is `supported` or `limited` and the generated answer is the insufficient-context phrase, build a context-only fallback answer from retrieved evidence lines
  - record the guard in debug meta as `invoke.answer_guard.reason=supported_context_false_not_found`
- Added evidence extraction helpers in `services/query_service.py`:
  - skip source headers, markdown separators, code fences, malformed truncated table rows
  - prioritize exact status terms such as `graph-lite=hit` and `graph-lite=not-reported`
  - render table rows with explicit operator action wording
- Promoted `UDQ-BC-01` into a dedicated opt-in fixture file:
  - `docs/USER_DOC_QUERY_EVAL_QUESTION_SET.md`
  - `evals/user_doc_answer_level_eval_fixtures.jsonl`

The fixture is intentionally separate from `evals/answer_level_eval_fixtures.jsonl` so the default `generic-baseline` gate does not require `project_docs` to be indexed on a fresh default runtime.

## Validation

Target tests:

```bash
./.venv/bin/python -m pytest -q tests/test_query_service.py tests/api/test_query_api.py tests/test_user_doc_eval_fixtures.py
```

Result: `51 passed`

Syntax check:

```bash
env PYTHONPYCACHEPREFIX=/tmp/trunk-rag-pycache ./.venv/bin/python -m py_compile services/query_service.py api/routes_query.py
```

Result: passed

User-doc answer eval:

```bash
./.venv/bin/python scripts/eval_query_quality.py \
  --base-url http://127.0.0.1:8015 \
  --timeout-seconds 90 \
  --eval-file evals/user_doc_answer_level_eval_fixtures.jsonl \
  --case-id UDQ-BC-01 \
  --llm-provider ollama \
  --llm-model gemma4:e4b \
  --llm-base-url http://localhost:11434 \
  --query-timeout-seconds 60 \
  --output-json docs/reports/user_doc_query_answer_eval_2026-04-30_loop126.json \
  --output-report docs/reports/USER_DOC_QUERY_ANSWER_EVAL_2026-04-30_LOOP126.md
```

Result:

- cases: `1`
- passed: `1`
- pass_rate: `1.0`
- avg_weighted_score: `1.0`
- support_pass_rate: `1.0`
- source_route_pass_rate: `1.0`
- p95_latency_ms: `12349.821`

## Decision

`UDQ-BC-01` is promoted to the dedicated user-doc fixture file, not the default baseline fixture file.

Next recommended loop:

`LOOP-127 User-doc quality gate operator command`

Goal: make the opt-in user-doc eval gate repeatable as a documented command or small wrapper without changing the default release gate.
