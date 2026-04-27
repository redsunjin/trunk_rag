# V1.5 reindex live adapter post-smoke enablement checkpoint review

Date: 2026-04-22
Loop: `LOOP-068`

## Verdict

- Guarded local execution evidence: `Go`
- Top-level apply success promotion: `No-Go`
- Next implementation planning: `Go`

## Basis

`LOOP-067` proved the explicit local-only guarded command can run `index_service.reindex()` and return runtime sidecar evidence:

- `requested_live_binding_stage=guarded_live_executor`
- `selection_state=guarded_live_executor`
- `actual_runtime_handler=index_service.reindex`
- `actual_runtime_handler_invoked=true`
- `runtime_chunks=37`
- `runtime_vectors=37`
- `runtime_scope=default_runtime_only`
- current top-level error remains `MUTATION_APPLY_NOT_ENABLED`
- top-level promotion gate remains disabled

This is enough to keep the guarded local executor path alive.

## No-Go Items

Top-level success promotion should not open yet for these reasons:

1. Failure detail is still not a first-class blocked apply sidecar.
   - The first guarded smoke attempt reached `index_service.reindex()` but failed on Chroma metadata validation.
   - Before the smoke check was tightened, that class of failure could still leave the high-level smoke suite looking healthy because only `MUTATION_APPLY_NOT_ENABLED` was checked.
   - The runtime should expose `mutation_executor_error` deterministically when the executor is invoked but does not return a result.

2. Durable audit currently records the pre-side-effect blocked request receipt, not the post-executor result/error.
   - The audit receipt is correctly created before side effects.
   - The result/error sidecar is currently response evidence, not durable post-execution evidence.
   - Top-level promotion should wait until this distinction is explicit.

3. Rollback evidence is still advisory.
   - `rollback_hint.mode=rebuild_from_source_documents` is appropriate for derivative vector state.
   - A real rollback drill is still not implemented and should stay out of the success gate until explicitly scoped.

## Next Implementation Scope

`LOOP-069 V1.5 reindex live adapter executor error sidecar draft` should:

- capture executor error output when `execute_mutation_request()` returns `ok=false`
- attach `mutation_executor_error` to blocked apply response/error contracts
- mark top-level promotion router failure route eligible when a supported executor error code is present
- add smoke summary coverage for executor error evidence
- add tests using a monkeypatched `index_service.reindex()` failure

## Verification

- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`
