# V1.5 Mutation Audit Retention Ops Draft - 2026-04-18

## Scope

- 대상 루프: `LOOP-039 V1.5 mutation audit retention ops draft`
- 기준 상태: `LOOP-038` upload review executor boundary review 반영 이후
- 목적: `90일 rolling_window` retention, explicit prune ownership, staged activation과 충돌하지 않는 operator-facing audit ops 문구를 코드/테스트/문서 기준으로 고정한다.

## Decision

- durable mutation audit backend는 계속 `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file` explicit local config일 때만 사용한다.
- retention 기간은 계속 `90일`로 고정한다.
- prune는 자동 job이 아니라 `local_operator`의 명시적 수동 작업으로 남긴다.
- live mutation execution readiness는 retention/prune 운영 문구가 먼저 문서화돼 있어야 한다.
- 이번 단계에서도 retention 기간을 env로 열거나 prune scheduler를 추가하지 않는다.

## Ops Contract

`services/tool_audit_sink_service.py`의 local file receipt와 stored entry는 nested `ops` 계약을 함께 남긴다.

```json
{
  "storage_scope": "local_runtime_tree",
  "storage_root_dir": "/.../chroma_db/mutation_audit",
  "retention_days": 90,
  "rotation_unit": "day",
  "prune_policy": "rolling_window",
  "prune_owner": "local_operator",
  "prune_mode": "explicit_manual",
  "runbook_required": true,
  "activation_dependency": "retention_ops_documented"
}
```

고정 의미:

- `prune_owner=local_operator`
  - 코드 merge나 runtime worker가 아니라 로컬 운영자가 prune 책임을 진다.
- `prune_mode=explicit_manual`
  - 백그라운드 자동 삭제를 하지 않는다.
- `activation_dependency=retention_ops_documented`
  - `reindex` live readiness는 retention/prune 운영 문구가 먼저 정리돼 있어야 한다.

## Operator Notes

1. 기본값은 여전히 `null_append_only`다.
2. local audit file이 필요할 때만 `DOC_RAG_MUTATION_AUDIT_BACKEND=local_file`을 명시한다.
3. local file backend를 켠 뒤 생성된 `audit-YYYYMMDD.jsonl`과 `sequence_state.json`은 `chroma_db/mutation_audit/` 또는 configured dir 아래에 남는다.
4. `90일`보다 오래된 audit file prune는 자동화하지 않고, 로컬 운영자가 명시적으로 수행한다.
5. prune 전에는 current-day log와 `sequence_state.json`를 보존하고, staged activation/runbook 판단과 충돌하지 않는지 확인한다.

## Non-goals

- prune scheduler 또는 background cleanup job 구현
- retention 기간의 runtime config화
- live mutation execution 개방
- upload review live executor 개방

## Validation

- `./.venv/bin/python -m pytest -q tests/test_mutation_executor_service.py tests/test_tool_audit_sink_service.py tests/test_agent_runtime_service.py tests/test_tool_middleware_service.py tests/test_smoke_agent_runtime.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `git diff --check`

결과:

- `38 passed`
- `[roadmap-harness] ready`
- formatting/whitespace issue 없음

## Next Step

다음 loop는 `LOOP-040 V1.5 reindex live readiness checklist draft`다. 이 단계에서는 `reindex` activation seam, upload review boundary, retention ops 문구를 합쳐 live enablement readiness checklist를 정리한다.
