# V1.5 Reindex Activation Operator Runbook Draft - 2026-04-19

## Scope

- 대상 루프: `LOOP-043 V1.5 reindex activation operator runbook draft`
- 목적: `reindex` staged activation을 local operator 관점에서 점검하는 절차를 정리한다.
- 전제: 이 runbook은 live execution을 여는 문서가 아니라, activation precondition과 checkpoint 확인 절차를 운영 문서로 번역한 초안이다.

## Guardrails

1. 대상 tool은 `reindex` 하나로 제한한다.
2. public `/agent/*` endpoint는 여전히 범위 밖이다.
3. upload review(`approve_upload_request`, `reject_upload_request`)는 별도 boundary로 남겨 두고 이 runbook에 넣지 않는다.
4. actual live adapter가 없으므로 apply는 끝까지 `MUTATION_APPLY_NOT_ENABLED`여야 한다.

## Preflight Checklist

runbook 실행 전 아래를 모두 만족해야 한다.

- `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md`를 읽고 현재 verdict가 여전히 `No-Go`임을 확인한다.
- `docs/reports/V1_5_REINDEX_LIVE_READINESS_CHECKLIST_DRAFT_2026-04-19.md`와 `docs/reports/V1_5_REINDEX_ACTIVATION_CHECKPOINT_REVIEW_2026-04-19.md`를 기준 문서로 둔다.
- local audit backend는 `local_file`로만 취급한다.
- retention/prune ownership은 `90일 rolling_window`, `local_operator`, `explicit_manual` 기준을 따른다.
- upload review live execution은 이번 절차에서 다루지 않는다.

## Step 1. Baseline Default Smoke

먼저 기본 경로가 여전히 off-by-default인지 확인한다.

명령:

```bash
./.venv/bin/python scripts/smoke_agent_runtime.py
```

기대 결과:

- overall `ok=true`
- `write_tool_apply_not_enabled.summary.error_code=MUTATION_APPLY_NOT_ENABLED`
- `write_tool_apply_not_enabled.summary.mutation_executor.executor_name=noop_mutation_executor`
- `write_tool_apply_not_enabled.summary.mutation_executor.selection_state=noop_fallback`
- `write_tool_apply_not_enabled.summary.mutation_executor.activation_blocked_by`에 `activation_not_requested`, `durable_audit_not_ready`가 포함된다.

이 단계가 깨지면 activation precondition을 보기 전에 기본 safety rail부터 다시 점검해야 한다.

## Step 2. Local Audit Backend 준비

activation checkpoint를 볼 때는 durable local audit receipt가 필요하다.

권장 환경 변수:

```bash
DOC_RAG_MUTATION_AUDIT_BACKEND=local_file
DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag_mutation_audit_checkpoint
DOC_RAG_AGENT_MUTATION_EXECUTION=1
```

운영 메모:

- audit dir는 local runtime tree 성격의 경로를 사용한다.
- append-only receipt는 `sequence_id`, `storage_path`, `retention_days=90`, `prune_policy=rolling_window`를 반환해야 한다.
- prune는 자동화하지 않고 local operator가 수동으로 책임진다.

## Step 3. Activation Check Smoke

다음 명령으로 activation request + durable local audit receipt가 함께 있을 때의 candidate path를 점검한다.

```bash
env DOC_RAG_AGENT_MUTATION_EXECUTION=1 \
  DOC_RAG_MUTATION_AUDIT_BACKEND=local_file \
  DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag_mutation_audit_checkpoint \
  ./.venv/bin/python scripts/smoke_agent_runtime.py
```

기대 결과:

- overall `ok=true`
- `write_tool_apply_not_enabled.summary.audit_sink.sink_type=local_file_append_only`
- `write_tool_apply_not_enabled.summary.audit_sink.sequence_id`가 양수다.
- `write_tool_apply_not_enabled.summary.mutation_executor.executor_name=reindex_mutation_adapter_stub`
- `write_tool_apply_not_enabled.summary.mutation_executor.selection_state=candidate_stub`
- `write_tool_apply_not_enabled.summary.mutation_executor.selection_reason=activation_guard_satisfied`
- `write_tool_apply_not_enabled.summary.mutation_executor.activation_blocked_by=[]`

중요:

- 여기서도 apply는 성공하면 안 된다.
- expected end state는 여전히 `MUTATION_APPLY_NOT_ENABLED`다.
- 현재 runbook의 목적은 "candidate path가 보이는지" 확인하는 것이지, live execution success를 만드는 것이 아니다.

## Step 4. Audit Receipt 확인

activation check smoke 이후 local audit tree를 확인한다.

확인 대상:

- `${DOC_RAG_MUTATION_AUDIT_DIR}/audit-YYYYMMDD.jsonl`
- `${DOC_RAG_MUTATION_AUDIT_DIR}/sequence_state.json`

기대 결과:

- `audit-*.jsonl`에 append-only entry가 추가된다.
- `sequence_state.json`의 `last_sequence_id`가 증가한다.
- entry/receipt에 `retention_days=90`, `prune_policy=rolling_window`, nested `ops.prune_owner=local_operator`, `ops.prune_mode=explicit_manual`가 남아 있다.

## Step 5. Deactivation

checkpoint 확인이 끝나면 기본값으로 되돌린다.

정리 원칙:

- `DOC_RAG_AGENT_MUTATION_EXECUTION`은 다시 unset 상태로 둔다.
- 필요하지 않으면 `DOC_RAG_MUTATION_AUDIT_BACKEND`도 기본값(`null`)로 되돌린다.
- default smoke를 다시 실행해 `noop_fallback` 경로가 복원되는지 확인한다.

## Abort Conditions

아래 중 하나라도 발생하면 runbook을 중단하고 live enablement 논의를 멈춘다.

1. apply가 `MUTATION_APPLY_NOT_ENABLED`를 지나 실제 성공으로 보인다.
2. `audit_sink.sink_type`가 `local_file_append_only`가 아니거나 durable receipt가 비어 있다.
3. upload review tool이 같은 절차로 섞여 들어온다.
4. public `/agent/*` surface나 외부 노출 경로가 전제된다.
5. operator가 retention/prune ownership을 확인할 수 없다.

## Non-goals

- actual `reindex` live adapter 구현
- actual live execution enablement
- upload review operator runbook
- prune 자동화

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`
- `env DOC_RAG_AGENT_MUTATION_EXECUTION=1 DOC_RAG_MUTATION_AUDIT_BACKEND=local_file DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag_mutation_audit_checkpoint ./.venv/bin/python scripts/smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-044 V1.5 reindex live adapter outline draft`다. 이 단계에서는 runbook 다음에 필요한 actual live adapter 책임과 경계를 outline 수준으로만 정리한다.
