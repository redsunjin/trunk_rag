# V1.5 reindex live adapter public promotion blocker register

Date: 2026-04-22
Loop: `LOOP-081`

## Decision

Default/public top-level promotion remains `No-Go`.

The explicit local-only operator/test path is sufficiently evidenced for local use, but public behavior needs a separate product, safety, audit, and recovery surface.

## Local-Only Conditions Already Satisfied

1. explicit activation
   - `DOC_RAG_AGENT_MUTATION_EXECUTION=1`
   - live binding opt-in
   - guarded executor stage opt-in
   - extra top-level promotion opt-in

2. policy gates
   - admin auth gate
   - mutation intent gate
   - preview requirement
   - apply envelope validation
   - default path still blocked by `MUTATION_APPLY_NOT_ENABLED`

3. executor evidence
   - `reindex_mutation_adapter_live`
   - `guarded_live_executor`
   - direct runtime handler: `index_service.reindex`
   - runtime chunks/vectors evidence
   - success and failure sidecars
   - adapter-specific failure taxonomy

4. audit evidence
   - local append-only audit backend
   - stable pre-executor audit sequence
   - post-executor `mutation_executor_post_execution` record
   - pre/post sequence linkage

5. operator evidence
   - operator runbook distinguishes default blocked, guarded blocked, and guarded top-level promotion commands
   - rollback drill plan, harness, and execution evidence exist
   - rollback drill result: `ok=true`, audit linkage `6 -> 7`, recovery rebuild `37/37`, post-recovery vector count `37`

## Public Promotion Blockers

1. Product/API contract
   - No public route or user-facing contract exists for live mutation execution.
   - No confirmation UX defines who may trigger reindex, what impact is shown, or how cancellation is handled.

2. Authorization model
   - Current evidence is local operator/admin only.
   - Public/default behavior would need role, tenant, and deployment policy boundaries that are not specified here.

3. Audit backend
   - Current durable evidence is local-file append-only.
   - Public behavior needs an agreed retention/export/security model beyond local runtime storage.

4. Recovery model
   - Current rollback recovery is rebuild-from-source for derivative vector state.
   - Public behavior needs documented data ownership, backup/snapshot expectations, failure handling, and repeated drill evidence.

5. Concurrency and job lifecycle
   - No public job status, cancellation, idempotency, lock, or concurrent reindex policy is defined.
   - Public callers must not be able to trigger overlapping destructive rebuilds.

6. Upload review boundary
   - Upload review live execution remains `boundary_noop`.
   - Public promotion must not bypass upload review approval or document provenance checks.

7. Observability and support
   - No public alerting, operator notification, or user-facing error recovery contract exists.
   - Current warnings from local dependencies are non-blocking locally but should not be treated as public-quality telemetry.

8. Regression scope
   - Existing V1 query/upload/admin paths must remain unaffected.
   - Public mutation enablement would require broader regression and user journey proof than the local-only smoke/drill suite.

## Future Minimum Evidence

Before any broader Go decision, at minimum:

- public API/UX contract for live reindex mutation
- role/tenant authorization policy
- production-grade audit backend or explicit deployment constraint
- concurrency lock and job lifecycle behavior
- repeated rollback drill evidence, including failure path
- upload review boundary decision
- V1 query/upload/admin regression proof
- operator support and incident procedure

## Next Step

Prepare a local-only live adapter closeout that states the current terminal scope: `reindex` explicit local-only operator/test surface is `Go`; default/public promotion and upload review live execution remain `No-Go`.
