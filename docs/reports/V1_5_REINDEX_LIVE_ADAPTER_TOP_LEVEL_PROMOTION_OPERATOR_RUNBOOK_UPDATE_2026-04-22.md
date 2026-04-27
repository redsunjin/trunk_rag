# V1.5 reindex live adapter top-level promotion operator runbook update

Date: 2026-04-22
Loop: `LOOP-075`

## Decision

`Go` for post-runbook enablement checkpoint review.

The operator runbook now distinguishes default blocked, activation check, guarded blocked, and guarded top-level promotion paths.

## Updates

1. Guardrails
   - Default smoke, activation smoke, and guarded blocked smoke must remain `MUTATION_APPLY_NOT_ENABLED`.
   - Top-level `ok=true` is allowed only for the explicit local-only guarded promotion command.
   - Default/public promotion remains blocked until rollback drill and broader enablement are explicitly scoped.

2. Commands
   - Added guarded blocked command:
     `--opt-in-live-binding --opt-in-live-binding-stage-guarded`
   - Added guarded top-level promotion command:
     `--opt-in-live-binding --opt-in-live-binding-stage-guarded --opt-in-top-level-promotion`
   - Added env opt-in:
     `DOC_RAG_MUTATION_SMOKE_TOP_LEVEL_PROMOTION=1`

3. Audit verification
   - Operators must verify `mutation_executor_post_execution` receipt presence.
   - Operators must verify pre/post sequence linkage.
   - Top-level success is acceptable only with linked post-executor audit evidence.

4. Abort conditions
   - Unexpected top-level success outside the explicit promotion command remains an abort.
   - Missing post-executor audit receipt is an abort.
   - Broken pre/post audit sequence linkage is an abort.
   - Upload review and public/external surface remain abort conditions.

## Verification

- `./.venv/bin/python scripts/roadmap_harness.py validate` -> `ready`

## Next Step

Run a post-runbook enablement checkpoint review to decide whether the current local-only operator surface is sufficient or whether rollback drill planning should become the next active implementation.

