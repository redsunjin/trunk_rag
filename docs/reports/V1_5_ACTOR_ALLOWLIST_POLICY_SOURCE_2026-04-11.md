# V1.5 Actor Allowlist Policy Source - 2026-04-11

## Scope

- 대상 루프: `LOOP-027 V1.5 actor allowlist policy source draft`
- 기준 커밋: `4c74ecf docs(agent): queue v1.5 policy follow-up loops`
- 목적: actor별 tool allowlist와 mutation 조건을 코드화하기 전에 policy source 초안을 고정한다.

## Current Baseline

현재 내부 runtime은 다음 기준으로만 동작한다.

- `services/agent_runtime_service.py`의 기본 allowlist는 `search_docs`, `read_doc`, `list_collections`, `health_check`, `list_upload_requests`다.
- `services/tool_middleware_service.py`는 `tool_allowlist`와 `unsafe_action_guard`를 순차 적용한다.
- write tool은 `ToolContext.allow_mutation=True`가 없으면 막히지만, actor category별 auth/intent/preview 정책은 아직 없다.

이 문서는 "지금 코드가 이미 안전하다"를 주장하는 문서가 아니다. 현재 read-only default를 유지하되, 다음 loop가 어떤 policy source를 구현해야 하는지 경계를 고정하는 문서다.

## Tool Inventory

현재 등록된 tool은 아래 네 그룹으로 본다.

| tool_group | tools | side_effect | 비고 |
| --- | --- | --- | --- |
| `read_query` | `search_docs`, `read_doc`, `list_collections`, `health_check` | read | 일반 query/runtime 진단 경로 |
| `read_admin` | `list_upload_requests` | read | 관리자 검토용 읽기 경로 |
| `write_upload_review` | `approve_upload_request`, `reject_upload_request` | write | 업로드 요청 승인/반려 |
| `write_index_maintenance` | `reindex` | write | 인덱스 재생성/유지보수 |

정책 초안 기준 핵심 구분은 다음과 같다.

- `read_query`는 기본 actor가 사용할 수 있는 최소 범위다.
- `read_admin`은 side effect는 없지만 운영/관리 맥락이 필요하므로 일반 query actor와 분리한다.
- `write_upload_review`와 `write_index_maintenance`는 둘 다 write지만 승인 조건이 같지 않다.

## Actor Categories

`actor` 문자열 자체를 곧바로 권한으로 쓰지 않고, 먼저 `actor_category`로 정규화한다고 가정한다.

| actor_category | 기본 read groups | mutation candidate groups | 설명 |
| --- | --- | --- | --- |
| `internal_read_only` | `read_query` | 없음 | 현재 `internal_agent` 기본 경로. query/retrieval 중심 |
| `admin_read_only` | `read_query`, `read_admin` | 없음 | 인증된 관리자 진단/검토 전용 읽기 경로 |
| `admin_review_mutation` | `read_query`, `read_admin` | `write_upload_review` | 승인/반려 검토를 수행하는 관리자 actor |
| `maintenance_mutation` | `read_query` 중 `health_check`, `list_collections` + 필요 시 `read_admin` 없음 | `write_index_maintenance` | reindex 같은 유지보수 작업 전용 actor |
| `unknown_read_only` | `health_check` | 없음 | 미해석 actor fallback. write 승격 금지 |

메모:

- `unknown_read_only`는 "권한 미상 actor는 절대 mutation 후보를 얻지 않는다"는 안전 기준을 위한 fallback이다.
- `internal_read_only`가 현재 기본 actor이며, `list_upload_requests`를 같은 read-only 묶음에 그대로 두는 것은 다음 loop에서 재검토한다.
- `maintenance_mutation`은 업로드 승인/반려와 `reindex`를 같은 write 권한으로 묶지 않기 위한 분리다.

## Policy Source Shape

다음 loop 구현 기준 source shape는 아래 수준이면 충분하다.

```json
{
  "schema_version": "v1.5.actor_policy_source.v1",
  "default_actor_category": "internal_read_only",
  "tool_groups": {
    "read_query": ["search_docs", "read_doc", "list_collections", "health_check"],
    "read_admin": ["list_upload_requests"],
    "write_upload_review": ["approve_upload_request", "reject_upload_request"],
    "write_index_maintenance": ["reindex"]
  },
  "actors": {
    "internal_read_only": {
      "read_groups": ["read_query"],
      "mutation_groups": [],
      "requires_admin_auth": false,
      "requires_mutation_intent": false,
      "requires_preview_before_apply": false,
      "audit_scope": "request_only"
    }
  }
}
```

필수 필드는 아래 정도로 고정한다.

- `schema_version`
- `default_actor_category`
- `tool_groups`
- `actors.<category>.read_groups`
- `actors.<category>.mutation_groups`
- `actors.<category>.requires_admin_auth`
- `actors.<category>.requires_mutation_intent`
- `actors.<category>.requires_preview_before_apply`
- `actors.<category>.audit_scope`

## Effective Allowlist Rules

다음 구현에서 중요한 점은 "mutation candidate"와 "현재 실행 가능한 allowlist"를 같은 값으로 보지 않는 것이다.

1. actor resolver는 먼저 `read_allowed_tools`와 `mutation_candidate_tools`를 분리해서 계산한다.
2. 기본 runtime allowlist는 `read_allowed_tools`만 포함한다.
3. write tool은 actor category가 해당 mutation group을 가진다고 해서 바로 allowlist에 들어가지 않는다.
4. write tool은 아래 조건이 모두 충족될 때만 `effective_allowed_tools`로 승격된다.

- actor category가 해당 mutation group을 가진다.
- admin auth 또는 local operator auth가 확인된다.
- explicit mutation intent가 확인된다.
- preview/dry-run 선행 조건이 충족된다.
- audit persistence contract가 준비돼 있다.

즉, `allow_mutation=True`는 앞으로도 필요할 수 있지만 충분조건이 아니다.

## Mutation Gate Matrix

| tool_group | auth | intent | preview | audit persistence | 비고 |
| --- | --- | --- | --- | --- | --- |
| `write_upload_review` | admin auth 필수 | 필수 | 필수 | 필수 | 요청 id, 현재 상태, 대상 collection/doc_key 요약 필요 |
| `write_index_maintenance` | local operator 또는 admin auth 필수 | 필수 | 필수 | 필수 | target collection, reset 여부, compatibility bundle 포함 여부 요약 필요 |

preview에서 기대하는 최소 결과:

- `write_upload_review`: `request_id`, 현재 status, `request_type`, `doc_key`, 예상 side effect
- `write_index_maintenance`: 대상 collection, `reset`, `include_compatibility_bundle`, 영향 범위 요약

## Resolver Notes For LOOP-028

`LOOP-028`에서는 아래 수준까지만 구현하면 충분하다.

- policy source를 읽는 순수 resolver 또는 manifest loader
- `actor -> actor_category -> read_allowed_tools/mutation_candidate_tools/policy_flags` 변환
- 기존 `DEFAULT_AGENT_TOOL_ALLOWLIST` 상수를 policy source 기반 계산으로 치환
- trace/middleware에 `actor_category`, `mutation_candidate_tools`, `policy_flags` seed를 남길 최소 구조

이 단계에서는 아직 아래를 하지 않는다.

- 실제 admin auth 검증
- mutation intent parser
- preview payload 생성
- audit persistence 저장소 구현

## Test Candidates

### LOOP-028

- `internal_agent`가 `internal_read_only`로 해석된다.
- `admin`류 actor가 `admin_read_only` 또는 `admin_review_mutation`으로 해석되더라도 write tool은 즉시 허용되지 않는다.
- unknown actor는 `unknown_read_only` fallback으로 들어가며 mutation candidate가 비어 있다.
- runtime/middleware가 상수 allowlist가 아니라 policy source에서 계산한 read allowlist를 사용한다.

### LOOP-029

- admin auth 누락 시 write tool은 `AUTH_REQUIRED`류 코드로 차단된다.
- mutation intent 누락 시 `MUTATION_INTENT_REQUIRED`류 코드로 차단된다.
- preview 선행 필요 시 `PREVIEW_REQUIRED`류 코드로 차단된다.
- read-only actor는 기존 read tool 경로만 그대로 통과한다.

### LOOP-030

- preview payload가 최소 seed만 반환하고 raw content/admin code를 포함하지 않는다.
- persisted audit contract가 request id, actor category, tool, outcome, blocked_by, side effect를 남긴다.
- redaction 규칙이 `internal/public/persisted` audience 계약과 충돌하지 않는다.

## Non-goals

- public `/agent/*` endpoint 개방
- planner/worker 확장
- MCP tool orchestration
- 실제 write automation 허용

## Conclusion

`LOOP-027`의 결론은 "기본 read-only allowlist를 유지하되, 이후 write tool 개방은 actor category별 policy source와 auth/intent/preview/audit 조건을 모두 거친 뒤에만 가능하다"는 점이다. 다음 구현 순서는 `resolver skeleton -> admin auth + mutation intent gate -> dry-run preview + audit persistence contract`로 고정한다.
