# User-Doc Quality Gate Operator Command

- Loop: `LOOP-127 User-doc quality gate operator command`
- Date: `2026-04-30`
- Scope: make the opt-in `project_docs` / user-doc answer eval gate repeatable without changing the default release gate.

## Command

```bash
./.venv/bin/python scripts/check_user_doc_quality_gate.py \
  --llm-provider ollama \
  --llm-model gemma4:e4b \
  --llm-base-url http://localhost:11434 \
  --query-timeout-seconds 60 \
  --output-json docs/reports/user_doc_quality_gate_latest.json \
  --output-report docs/reports/USER_DOC_QUALITY_GATE_LATEST.md
```

## Boundary

- Default release gate remains `scripts/check_ops_baseline_gate.py` with `generic-baseline`.
- User-doc gate uses `evals/user_doc_answer_level_eval_fixtures.jsonl`.
- Default selected case is `UDQ-BC-01`.
- Required collection is explicit-only `project_docs`.
- The gate does not add `project_docs` to the default runtime collection path.
- The gate does not promote user-doc fixtures into `evals/answer_level_eval_fixtures.jsonl`.
- The gate does not change model defaults.

## Preconditions

- Local app server is running.
- LLM runtime is reachable by the selected provider/model/base URL.
- `project_docs` has indexed vectors.

If the script returns `PROJECT_DOCS_REINDEX_REQUIRED`, reindex `project_docs` before retrying:

```bash
./.venv/bin/python -c "from services import index_service; import json; result=index_service.reindex_single_collection(reset=False, collection_key='project_docs'); print(json.dumps(result, ensure_ascii=False, indent=2))"
```

## Ready Criteria

- Runtime preflight is ready.
- `project_docs` vectors are present.
- Selected user-doc eval cases all pass.
- `support_pass_rate=1.0`.
- `source_route_pass_rate=1.0`.

Exit code `0` means ready. Exit code `1` means blocked and the diagnostics section should be used as the operator handoff.
