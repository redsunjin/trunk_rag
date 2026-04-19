# V1.5 Follow-up Policy - 2026-04-10

## Scope

- 대상 루프: `LOOP-023 V1.5 후속 정책/공개 API 여부 정리`
- 기준 커밋: `3e5609e docs(agent): record v1.5 post-merge validation`
- 목적: V1.5 내부 agent-ready runtime 기반을 public API나 운영 정책으로 승격하기 전 필요한 판단 기준을 정리한다.

## Decisions

### 1. Public `/agent/*` API

결정: 지금은 공개하지 않는다.

이유:
- `agent_runtime_service.run_agent_entry()`는 내부 single-tool draft이며, 사용자에게 노출할 answer generation/UX 계약이 없다.
- `search_docs`는 retrieval context를 반환할 뿐 최종 답변을 생성하지 않는다.
- 현재 V1 사용자 기본 경로는 `/query`이며, 이 경로를 대체할 근거가 없다.

다음 조건이 충족되면 재검토한다:
- public response schema, auth, rate/timeout, error shape가 문서화된다.
- agent entry가 최소 1개 사용자 가치 흐름을 `/query`와 명확히 다르게 제공한다.
- live gate 외에 agent-specific smoke test가 생긴다.

### 2. Execution Trace Persistence

결정: 지금은 response-local metadata로 유지하고, persistence는 보류한다.

이유:
- `execution_trace`는 현재 내부 schema 검증 목적이며 운영 감사 저장소가 없다.
- 파일/DB 저장을 시작하면 retention, 민감 정보, 용량, 검색 정책이 필요하다.
- write tool audit persistence는 admin auth 정책과 함께 설계해야 한다.

다음 조건이 충족되면 재검토한다:
- trace redaction 규칙이 정해진다.
- request id 기준 조회 UX 또는 admin endpoint 필요성이 확인된다.
- storage backend와 retention 기간이 정해진다.

### 3. Actor Allowlist and Mutation Policy

결정: 기본은 read-only allowlist로 유지한다.

현재 기본 허용:
- `search_docs`
- `read_doc`
- `list_collections`
- `health_check`
- `list_upload_requests`

현재 기본 차단:
- `reindex`
- `approve_upload_request`
- `reject_upload_request`

write tool을 agent runtime에 열기 전 필요한 조건:
- actor별 policy source가 생긴다.
- admin auth와 mutation intent 확인이 붙는다.
- dry-run 또는 preview 결과가 먼저 제공된다.
- audit persistence가 준비된다.

2026-04-11 구현 메모:
- actor category, tool group, mutation gate, preview/audit 선행조건 초안은 `docs/reports/V1_5_ACTOR_ALLOWLIST_POLICY_SOURCE_2026-04-11.md`에 분리했다.
- 후속 구현 순서는 `resolver skeleton -> admin auth + mutation intent gate -> dry-run preview + audit persistence contract`로 고정한다.
- 같은 날짜 `config/actor_policy_manifest.json` + `services/actor_policy_service.py`로 resolver skeleton을 추가해 runtime/middleware가 actor category별 read allowlist와 mutation candidate metadata를 읽도록 정리했다.
- 같은 날짜 `services/tool_middleware_service.py`에 `mutation_policy_guard`를 추가해 mutation candidate write를 `ADMIN_AUTH_REQUIRED`/`ADMIN_AUTH_FAILED`/`MUTATION_INTENT_REQUIRED`/`PREVIEW_REQUIRED`로 분리 차단하고, `services/agent_runtime_service.py`는 `admin_code`/`mutation_intent` presence를 entry metadata에 남기도록 정리했다.
- 2026-04-12에는 `docs/reports/V1_5_PREVIEW_AUDIT_CONTRACT_2026-04-12.md`와 `services/tool_trace_service.py`의 `build_preview_contract()`/`build_persisted_audit_record()`로 preview payload contract와 persisted audit record contract를 고정했다.
- 같은 날짜 후속으로 `docs/reports/V1_5_PREVIEW_SEED_AUDIT_SINK_2026-04-12.md`, `services/tool_preview_service.py`, `services/tool_audit_sink_service.py`를 추가해 preview seed builder와 append-only audit sink interface를 연결했다.
- preview-confirmed apply envelope와 apply handshake guard까지는 반영됐다.
- `docs/reports/V1_5_MUTATION_EXECUTION_GO_NO_GO_REVIEW_2026-04-17.md`에서 실제 mutation execution `No-Go`, local append-only backend 방향, retention/activation ownership, `reindex` 우선 live scope를 고정했다.
- `docs/reports/V1_5_REINDEX_EXECUTOR_ACTIVATION_SEAM_DRAFT_2026-04-18.md`에서 `reindex` activation request, durable audit readiness, noop fallback/candidate stub selection 기준을 고정했다.
- `docs/reports/V1_5_UPLOAD_REVIEW_EXECUTOR_BOUNDARY_REVIEW_2026-04-18.md`에서 upload review execution을 `reindex`와 분리된 `boundary_noop`/rollback-audit precondition 기준으로 고정했다.
- `docs/reports/V1_5_MUTATION_AUDIT_RETENTION_OPS_DRAFT_2026-04-18.md`에서 `90일 rolling_window`, explicit local-operator prune ownership, nested `ops` receipt contract를 고정했다.
- `docs/reports/V1_5_REINDEX_LIVE_READINESS_CHECKLIST_DRAFT_2026-04-19.md`에서 `reindex` live enablement 전 필요한 checklist/evidence 항목을 고정했다.

### 4. Branch Cleanup and Publish

상태:
- `main`은 `a429fe1 merge: v1.5 agent-ready runtime prep`와 `3e5609e docs(agent): record v1.5 post-merge validation`을 포함한다.
- `main`은 `origin/main`에 push 완료됐다.
- `feature/loop-017-tool-registry-skeleton`은 병합 완료 상태지만, 삭제는 되돌리기 어려운 정리 작업이므로 별도 명시 지시 전까지 보존한다.
- 기존 untracked `.DS_Store`, `TRUNK_RAG_LINKS.md`는 작업 범위 밖이므로 그대로 둔다.

## Immediate Next Steps

1. Public API는 만들지 않는다.
2. V1 기본 `/query` 경로는 유지한다.
3. agent runtime은 내부 service + unit test + smoke script 기준으로만 유지한다.
4. 다음 구현 후보는 `mutation activation smoke evidence draft`로 제한한다.

## Smoke Check

`scripts/smoke_agent_runtime.py`로 내부 runtime entry의 최소 경로를 점검한다.

```text
./.venv/bin/python scripts/smoke_agent_runtime.py
ok=true
read_only_health_check=true
write_tool_blocked_read_only=true
write_tool_requires_admin_auth=true
write_tool_requires_mutation_intent=true
write_tool_requires_preview=true
```

## Trace Redaction Follow-up

Trace 저장/노출 전 redaction 기준은 `docs/reports/V1_5_TRACE_REDACTION_POLICY_2026-04-10.md`에 분리했다.

결정:
- raw input, retrieved context, document content, local path, admin code, credential은 저장/노출 기본 대상에서 제외한다.
- 기본 저장 후보는 request id, tool name, side effect, runtime elapsed, route seed, outcome code, middleware blocked_by 같은 diagnostic seed로 제한한다.
- `redact_execution_trace()` 순수 함수와 `internal/public/persisted` audience별 단위 테스트를 추가했다.
- 이후 구현은 actor policy source, mutation gate, preview/audit contract, preview seed/audit sink, mutation apply guard, execution go/no-go review, mutation executor interface draft, durable mutation audit backend skeleton, reindex executor activation seam, upload review executor boundary review, mutation audit retention ops draft, reindex live readiness checklist draft 순서로 진행됐고 현재 다음 후보는 `mutation activation smoke evidence draft`다.

## Deferred

- `/agent/query` public endpoint
- MCP tool orchestration
- planner/worker runtime
- skill registry
- write tool automation
- GraphRAG 재개

## Conclusion

V1.5 결과물은 `main`에 병합됐지만 아직 public agent product가 아니다. 다음 단계는 기능 확장보다 정책 경계 고정이 우선이며, public API는 별도 loop에서 schema/auth/test 기준이 생긴 뒤에만 열어야 한다.
