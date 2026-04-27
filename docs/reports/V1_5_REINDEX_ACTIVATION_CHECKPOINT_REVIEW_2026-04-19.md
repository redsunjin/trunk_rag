# V1.5 Reindex Activation Checkpoint Review - 2026-04-19

## Scope

- 대상 루프: `LOOP-042 V1.5 reindex activation checkpoint review`
- 기준 상태: `LOOP-041` mutation activation smoke evidence 반영 이후
- 목적: `reindex` staged activation에 필요한 checklist/evidence를 다시 점검하고, live enablement 여부가 아니라 남은 blocker와 다음 문서화 단계를 고정한다.

## Checkpoint Inputs

- `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md`
- `docs/reports/V1_5_REINDEX_LIVE_READINESS_CHECKLIST_DRAFT_2026-04-19.md`
- `docs/reports/V1_5_MUTATION_ACTIVATION_SMOKE_EVIDENCE_2026-04-19.md`
- `env DOC_RAG_AGENT_MUTATION_EXECUTION=1 DOC_RAG_MUTATION_AUDIT_BACKEND=local_file DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag_mutation_audit_checkpoint ./.venv/bin/python scripts/smoke_agent_runtime.py`

## Checkpoint Verdict

- `reindex` live enablement verdict: `No-Go`
- next planning verdict: `Go` for operator runbook drafting

이번 checkpoint에서 확인한 것은 "지금 켤 수 있는가"보다 "무엇이 이미 준비됐고 무엇이 아직 빠졌는가"다. 결론은 다음과 같다.

1. staged activation precondition과 blocked-flow evidence는 충분히 문서화됐다.
2. activation request + durable local audit receipt가 있으면 `reindex`는 `candidate_stub`까지는 올라간다.
3. 하지만 실제 live execution adapter와 operator runbook은 아직 없으므로 enablement 판단은 여전히 `No-Go`다.

## Checkpoint Matrix

| checkpoint item | status | evidence | checkpoint note |
| --- | --- | --- | --- |
| internal service only surface 유지 | pass | `LOOP-034`, `LOOP-040` | public `/agent/*` 없이 internal runtime 경계만 남아 있다. |
| operator explicit activation 기본값 `off` | pass | default smoke evidence | 기본 경로는 `activation_not_requested` 상태로 머문다. |
| durable local audit receipt 경로 존재 | pass | `LOOP-036`, local-file smoke | `local_file_append_only`, `sequence_id`, `storage_path`가 실제로 관찰된다. |
| retention/prune ownership 문서화 | pass | `LOOP-039` | `90일 rolling_window`, `local_operator`, `explicit_manual` 기준이 고정돼 있다. |
| `reindex` candidate stub 승격 조건 확인 | pass | activation-on local-file smoke | `selection_state=candidate_stub`, `selection_reason=activation_guard_satisfied`가 실제로 관찰된다. |
| upload review separate boundary 유지 | pass | `LOOP-038` | upload review는 이번 checkpoint에 포함하지 않고 `boundary_noop`로 유지한다. |
| 실제 live adapter 구현 | open | current executor contract | 현재는 `reindex_mutation_adapter_stub`만 있고 apply는 여전히 `MUTATION_APPLY_NOT_ENABLED`다. |
| operator runbook/activation 절차 | open | current docs | local operator가 언제 무엇을 확인하고 어떤 순서로 staged activation을 다루는지 절차 문서가 아직 없다. |

## Activated Smoke Evidence

`DOC_RAG_AGENT_MUTATION_EXECUTION=1`과 `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file`를 함께 준 local smoke에서 아래가 확인됐다.

- `write_tool_apply_not_enabled.summary.audit_sink.sink_type=local_file_append_only`
- `write_tool_apply_not_enabled.summary.audit_sink.sequence_id=6`
- `write_tool_apply_not_enabled.summary.mutation_executor.executor_name=reindex_mutation_adapter_stub`
- `write_tool_apply_not_enabled.summary.mutation_executor.selection_state=candidate_stub`
- `write_tool_apply_not_enabled.summary.mutation_executor.selection_reason=activation_guard_satisfied`
- `write_tool_apply_not_enabled.summary.mutation_executor.activation_blocked_by=[]`

즉, activation seam 자체는 의도대로 동작한다. 현재 막혀 있는 이유는 activation guard가 아니라, live execution을 아직 일부러 열지 않았기 때문이다.

## Remaining Blockers

1. 실제 `reindex` live adapter는 아직 없다.
2. local operator용 staged activation runbook이 없다.
3. smoke evidence는 blocked path와 candidate stub path를 보여 주지만, live execution success path는 여전히 범위 밖이다.
4. upload review execution은 별도 boundary로 남아 있으며 이번 checkpoint에 합치지 않는다.

## Decision

- 이번 checkpoint는 `reindex` staged activation 토대가 충분히 정리됐음을 확인한다.
- 하지만 enablement 자체는 아직 열지 않는다.
- 다음 단계는 `LOOP-043`에서 operator runbook을 작성해 activation ownership, local config, audit receipt 확인, smoke 확인 순서를 운영 절차 관점에서 고정하는 것이다.

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/smoke_agent_runtime.py`
- `env DOC_RAG_AGENT_MUTATION_EXECUTION=1 DOC_RAG_MUTATION_AUDIT_BACKEND=local_file DOC_RAG_MUTATION_AUDIT_DIR=/tmp/trunk_rag_mutation_audit_checkpoint ./.venv/bin/python scripts/smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-043 V1.5 reindex activation operator runbook draft`다. 이 단계에서는 staged activation을 여는 문서가 아니라, local operator가 어떤 precondition과 checkpoint를 확인해야 하는지 runbook 형태로 정리한다.
