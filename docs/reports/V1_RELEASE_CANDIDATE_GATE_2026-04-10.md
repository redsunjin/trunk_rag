# V1 Release Candidate Gate - 2026-04-10

## Scope

- 대상 루프: `LOOP-016 V1 릴리즈 후보 실측 게이트/태그 준비`
- 검증 대상 코드 기준: `e7d98e0 docs(release): align v1 boundary sweep`
- 목적: V1 릴리즈 후보로 태그하기 전에 전체 회귀와 live `generic-baseline` 게이트를 재측정한다.

## Environment

- branch: `feature/loop-007-manifest-decouple`
- app base URL: `http://127.0.0.1:8000`
- LLM provider/model: `ollama + gemma4:e4b`
- LLM base URL: `http://localhost:11434`
- query timeout: `DOC_RAG_QUERY_TIMEOUT_SECONDS=30`
- embedding model: `BAAI/bge-m3`

## Verification Results

### Static/Unit Regression

```text
./.venv/bin/python -m pytest -q
141 passed in 8.00s
```

### Runtime Readiness

Initial live gate was blocked because the app health endpoint and Ollama API were not reachable. After starting the FastAPI app and confirming the existing Ollama server on port `11434`, `/health` reported:

- `status=ok`
- `vectors=37`
- `release_web_status=ready`
- `seed_corpus_role=demo_bootstrap`
- `seed_corpus_label=sample-pack demo/bootstrap corpus`
- `embedding_fingerprint_status=ready`
- `runtime_profile_status=verified`

### Live Generic Baseline Gate

```text
./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model gemma4:e4b --llm-base-url http://localhost:11434
[ops-baseline-gate] ready
eval_buckets=generic-baseline
cases=3
passed=3
pass_rate=1.0
avg_weighted_score=0.9467
p95_latency_ms=14058.994
```

## Tag Readiness

- Existing tag `v1.0.0` points to `6eb5329 docs(roadmap): define v1-v3 product path`.
- Current branch HEAD is `37` commits ahead of `v1.0.0`.
- Do not move or overwrite `v1.0.0`.
- The candidate is technically release-ready by current V1 gates.
- Because the current branch is not `main`, create the release tag only after one of these decisions:
  - merge this branch to the release target branch and tag there
  - explicitly tag the current branch

Recommended next tag name, if this remains a V1 stabilization release, is `v1.0.1`.

## Post-merge Main Validation

- merge commit: `ee4abef merge: feature loop 007 manifest decouple`
- target branch: `main`

```text
./.venv/bin/python -m pytest -q
141 passed in 6.01s
```

```text
./.venv/bin/python scripts/check_ops_baseline_gate.py --llm-provider ollama --llm-model gemma4:e4b --llm-base-url http://localhost:11434
[ops-baseline-gate] ready
eval_buckets=generic-baseline
cases=3
passed=3
pass_rate=1.0
avg_weighted_score=0.9467
p95_latency_ms=12565.988
```

Post-merge `main` is suitable for the `v1.0.1` tag.

## Conclusion

V1 release-candidate validation passes on post-merge `main`. Use `v1.0.1` for this V1 stabilization tag.
