# V1.5 reindex live adapter post-promotion enablement checkpoint review

Date: 2026-04-22
Loop: `LOOP-074`

## Verdict

- Extra opt-in local-only top-level promotion: `Go`
- Default/public top-level promotion: `No-Go`
- Operator runbook update: `Go`
- Rollback drill requirement for broader enablement: `Still blocking`

## Basis

`LOOP-073` proved the guarded top-level promotion path can be made explicit and auditable:

- default guarded path remains `MUTATION_APPLY_NOT_ENABLED`
- extra opt-in path requires `executor_binding.top_level_promotion_enabled`
- guarded success promotes to top-level `ok=true`
- eligible guarded failure can promote to the adapter error schema
- linked post-executor audit receipt is required before promotion
- real guarded promotion smoke returned `ok=true`
- durable post-executor audit record linked pre-executor sequence `6` to post-executor sequence `7`

This is enough to keep the path as an internal local-only operator/test surface.

## No-Go Items

Default/public enablement remains blocked:

1. Public `/agent/*` or user-facing mutation surface is still out of scope.
2. Upload review live execution remains `boundary_noop`.
3. Rollback is still advisory through `rollback_hint`, not a drilled restore procedure.
4. The operator runbook still describes the older activation-only expectation that apply must always end as `MUTATION_APPLY_NOT_ENABLED`.

## Next Implementation Scope

`LOOP-075 V1.5 reindex live adapter top-level promotion operator runbook update` should:

- update the operator runbook guardrails to distinguish default blocked, guarded blocked, and guarded top-level promotion paths
- add the `--opt-in-top-level-promotion` command and `DOC_RAG_MUTATION_SMOKE_TOP_LEVEL_PROMOTION=1` env surface
- record expected audit evidence for pre/post sequence linkage
- update abort conditions so top-level success is only acceptable in the explicit promotion command
- keep broader/public promotion and upload review live execution blocked

## Verification

- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`

