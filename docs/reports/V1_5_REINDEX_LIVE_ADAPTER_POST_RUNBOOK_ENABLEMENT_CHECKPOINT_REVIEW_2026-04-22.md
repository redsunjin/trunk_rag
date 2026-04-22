# V1.5 reindex live adapter post-runbook enablement checkpoint review

Date: 2026-04-22
Loop: `LOOP-076`

## Verdict

- Local-only operator surface: `Go`
- Default/public top-level promotion: `No-Go`
- Upload review live execution: `No-Go`
- Rollback drill planning: `Go`

## Basis

`LOOP-075` updated the operator runbook so the current live adapter surface is explicit:

- default blocked smoke remains `MUTATION_APPLY_NOT_ENABLED`
- activation check smoke remains `MUTATION_APPLY_NOT_ENABLED`
- guarded live executor smoke invokes `index_service.reindex()` but remains top-level blocked
- guarded top-level promotion smoke is allowed to return `ok=true` only with extra local-only promotion opt-in
- post-executor audit receipt and pre/post sequence linkage are required evidence
- abort conditions now cover unexpected success, missing post-executor audit receipt, broken sequence linkage, upload review leakage, and public/external surfaces

This is enough to preserve the current path as a local-only operator/test surface.

## No-Go Items

Broader/default/public promotion should remain blocked:

1. Rollback remains a hint (`rebuild_from_source_documents`), not a drilled restore procedure.
2. There is no documented drill that proves an operator can detect, recover, and re-verify the derivative vector state after a bad guarded reindex.
3. Upload review is still intentionally outside the live executor path.

## Next Implementation Scope

`LOOP-077 V1.5 reindex live adapter rollback drill plan draft` should:

- define a local-only rollback drill that does not widen public/default scope
- specify preconditions, test data assumptions, audit evidence, success metrics, and abort conditions
- decide what must be captured before and after `index_service.reindex()`
- define how to re-run rebuild-from-source recovery and verify vector counts/collection state
- keep actual drill execution as a separate later loop unless the plan proves it is safe to run immediately

## Verification

- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`

