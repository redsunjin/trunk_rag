# V1.5 Reindex Executor Activation Seam Draft - 2026-04-18

## Scope

- 대상 루프: `LOOP-037 V1.5 reindex executor activation seam draft`
- 기준 상태: `LOOP-036` durable audit backend skeleton 반영 이후
- 목적: 실제 live reindex execution을 열지 않은 상태에서 `reindex` 전용 activation guard, durable audit readiness 판정, noop fallback 전환 조건을 한 군데로 고정한다.

## Decision

- `services/mutation_executor_service.py`는 `resolve_mutation_executor(request)`에서 `reindex` activation selection을 중앙집중식으로 판단한다.
- `reindex`는 registered tool로 계속 취급하되, activation guard가 충족되지 않으면 default noop executor로 fallback한다.
- activation guard는 아래 두 조건을 함께 본다.
  - local operator explicit activation: `DOC_RAG_AGENT_MUTATION_EXECUTION=1`
  - durable audit readiness: `local_file_append_only` receipt + positive `sequence_id` + non-empty `storage_path`
- 두 조건이 모두 만족돼도 이번 단계에서는 실제 write를 열지 않고 `ReindexMutationExecutorAdapter` candidate stub까지만 선택한다.
- `approve_upload_request`, `reject_upload_request`는 여전히 unregistered live scope로 두고 default noop를 유지한다.

## Selection Rules

1. `tool_name != reindex`
   - `executor_name=noop_mutation_executor`
   - `selection_state=default_noop`
   - `selection_reason=tool_not_registered`
2. `tool_name == reindex` + activation guard 미충족
   - `executor_name=noop_mutation_executor`
   - `tool_registered=true`
   - `registered_executor_name=reindex_mutation_adapter_stub`
   - `selection_state=noop_fallback`
   - `selection_reason=activation_guard_blocked`
   - `activation.blocked_by`에 `activation_not_requested`, `durable_audit_not_ready`를 기록
3. `tool_name == reindex` + activation guard 충족
   - `executor_name=reindex_mutation_adapter_stub`
   - `selection_state=candidate_stub`
   - `selection_reason=activation_guard_satisfied`
   - `execution_enabled=false`는 그대로 유지

## Executor Contract Additions

- top-level:
  - `selection_state`
  - `selection_reason`
  - `registered_executor_name` (noop fallback일 때만)
- nested `activation`:
  - `surface_scope=internal_service_only`
  - `activation_source=local_env_flag`
  - `ownership=operator_local_config`
  - `env_key=DOC_RAG_AGENT_MUTATION_EXECUTION`
  - `first_live_tool_scope=reindex`
  - `durable_audit_required`
  - `durable_audit_ready`
  - `audit_sink_type`
  - `audit_sequence_id`
  - `audit_storage_path`
  - `blocked_by`

이 계약은 "왜 아직 noop인지"와 "candidate stub로 넘어갈 최소 조건이 충족됐는지"를 middleware/error/execution trace에서 같은 형태로 보여 주기 위한 것이다.

## Runtime/Test Integration

- `tests/test_mutation_executor_service.py`
  - `reindex` + activation off -> noop fallback
  - `reindex` + activation on + null sink -> noop fallback
  - `reindex` + activation on + durable local receipt -> candidate stub
  - upload review tool -> default noop
- `tests/test_tool_middleware_service.py`
  - preview-confirmed apply에서 default null sink 경로는 noop fallback contract를 남긴다.
  - local file sink + activation on 경로는 candidate stub contract를 남긴다.
- `tests/test_agent_runtime_service.py`
  - agent entry도 같은 selection contract를 error/execution trace에 노출한다.

## Non-goals

- 실제 `reindex` 실행 연결
- upload review live executor
- public `/agent/*` endpoint
- audit prune job 자동화

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

결과:

- `35 passed`
- `[roadmap-harness] ready`
- formatting/whitespace issue 없음

## Next Step

다음 loop는 `LOOP-038 V1.5 upload review executor boundary review`다. 이 단계에서는 upload review execution을 `reindex` activation seam과 섞지 않고 별도 위험 경계/rollback/audit precondition으로 분리한다.
