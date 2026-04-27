# V1.5 reindex live adapter rollback drill execution evidence

Date: 2026-04-22
Loop: `LOOP-079`

## Decision

`Go` for post-rollback-drill enablement checkpoint review.

The rollback drill passed in explicit local-only mode. This does not open default/public top-level promotion.

## Command

```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 DOC_RAG_MUTATION_AUDIT_BACKEND=local_file DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag-rollback-drill ./.venv/bin/python scripts/smoke_reindex_rollback_drill.py
```

Exit code: `0`

Non-blocking runtime warnings were observed:
- `urllib3` LibreSSL warning from the local Python runtime.
- Chroma telemetry `capture()` warnings.

## Evidence

1. env guard
   - `DOC_RAG_AGENT_MUTATION_EXECUTION=1`
   - audit backend: `local_file`
   - audit dir: `/tmp/trunk_rag-rollback-drill`
   - result: `ok=true`

2. pre-state capture
   - collection key: `all`
   - collection name: `w2_007_header_rag`
   - vector count: `37`

3. guarded top-level promotion smoke
   - selected executor: `reindex_mutation_adapter_live`
   - selection state: `guarded_live_executor`
   - runtime handler: `index_service.reindex`
   - runtime handler invoked: `true`
   - top-level promotion router: `enabled_explicit_local_only`
   - top-level promotion enabled: `true`
   - runtime chunks: `37`
   - runtime vectors: `37`
   - runtime scope: `default_runtime_only`

4. post-executor audit linkage
   - pre-executor audit sequence id: `6`
   - post-executor audit sequence id: `7`
   - post-executor record kind: `mutation_executor_post_execution`
   - audit storage: `/tmp/trunk_rag-rollback-drill/audit-20260422.jsonl`

5. recovery rebuild from source
   - command path: `index_service.reindex(reset=True, collection_key="all", include_compatibility_bundle=False)`
   - docs: `5`
   - chunks: `37`
   - vectors: `37`
   - reindex scope: `default_runtime_only`
   - compatibility bundle included: `false`

6. post-recovery state capture
   - collection key: `all`
   - collection name: `w2_007_header_rag`
   - vector count: `37`

7. audit file check
   - file: `/tmp/trunk_rag-rollback-drill/audit-20260422.jsonl`
   - line count after drill: `7`
   - final entry sequence id: `7`
   - final entry event: `mutation_executor.completed`
   - final entry elapsed: `8326ms`

## Result

The drill result schema was `v1.5.reindex_live_adapter_rollback_drill.v1` and top-level result was `ok=true`.

Rollback recovery evidence is sufficient for a checkpoint review:
- pre-state vector count stayed observable at `37`
- guarded top-level promotion ran with linked post-executor audit `6 -> 7`
- rebuild-from-source recovery produced `37` chunks and `37` vectors
- post-recovery vector count stayed `37`

## Next Step

Run post-rollback-drill enablement checkpoint review. Default/public top-level promotion remains `No-Go` until that checkpoint explicitly changes it.
