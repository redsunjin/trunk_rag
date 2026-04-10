# V1.5 Trace Redaction Policy - 2026-04-10

## Scope

- 대상 루프: `LOOP-025 V1.5 trace redaction policy draft`
- 대상 schema: `v1.5.tool_execution_trace.v1`
- 대상 코드: `services/tool_trace_service.py`, `services/tool_middleware_service.py`, `services/agent_runtime_service.py`
- 목적: `execution_trace`를 저장하거나 외부 API 응답으로 노출하기 전 필요한 redaction 기준을 고정한다.

## Current Position

현재 `execution_trace`는 response-local 내부 metadata다. 파일, DB, analytics backend에 저장하지 않으며 public `/agent/*` API로도 노출하지 않는다.

이 정책은 향후 trace persistence나 public exposure를 추가할 때의 선행 조건이다. 정책이 코드로 구현되기 전까지 trace를 장기 저장하거나 외부 사용자에게 그대로 반환하면 안 된다.

## Classification

| Class | Meaning | Default Action |
| --- | --- | --- |
| `safe` | 운영 진단에 필요하고 민감 정보 가능성이 낮은 필드 | 저장/노출 가능 |
| `conditional` | 내부 운영자에게는 유용하지만 외부 노출 전 추가 판단이 필요한 필드 | internal only 또는 축약 |
| `redact` | 진단에는 필요할 수 있으나 원문 저장/노출이 위험한 필드 | 마스킹/요약만 허용 |
| `drop` | 저장/노출 가치보다 위험이 큰 필드 | 저장/노출 금지 |

## Field Policy

### Safe

- `schema_version`
- `request_id`
- `actor`의 coarse category
- `runtime.timeout_seconds`
- `runtime.elapsed_ms`
- `policy.allow_mutation`
- `policy.allowed_tools`
- `tool.name`
- `tool.side_effect`
- `routing.query_profile`
- `routing.collections`
- `routing.route_reason`
- `routing.budget_profile`
- `middleware.blocked_by`
- `middleware.steps[].middleware`
- `middleware.steps[].status`
- `outcome.ok`
- `outcome.error.code`
- `outcome.error.status_code`
- `audit.events[].event`
- `audit.events[].elapsed_ms`

### Conditional

- `actor` raw value
- `middleware.steps[].detail`
- `audit.events[].tool`
- `audit.events[].actor`
- `tool.result_seed.origin`
- `tool.result_seed.collection_key`
- `tool.result_seed.doc_key`
- `tool.result_seed.source_name`
- `tool.result_seed.source_count`

조건:
- 내부 운영자 화면 또는 local-only diagnostic artifact에서는 허용할 수 있다.
- public API response에서는 `actor`는 role/category로 축약하고, `source_name`과 `doc_key`는 필요성이 확인될 때만 노출한다.
- `middleware.steps[].detail`은 key allowlist 방식으로만 노출한다.

### Redact

- user input / query text
- retrieved context text
- document content
- full error message
- raw payload
- local filesystem path
- upload source file name
- upload request free-text note
- decision note
- rejection reason text

처리:
- 원문 대신 length, hash, count, category, normalized code를 저장한다.
- error message는 `error.code`와 필요 시 짧은 generic message로 대체한다.
- local path는 basename도 기본 노출하지 않고 collection/doc key 수준으로 축약한다.

### Drop

- admin code
- API key/token/credential
- environment variable raw value
- full stack trace
- model prompt with retrieved context
- generated answer draft before final policy pass
- raw uploaded document body

처리:
- trace persistence 대상에서 제외한다.
- debug mode에서도 별도 명시 승인 없이 저장하지 않는다.

## Persistence Policy

Trace persistence를 구현하기 전 최소 조건:

1. redaction function이 `execution_trace`를 저장 전 정규화한다.
2. 저장 schema version을 `TRACE_SCHEMA_VERSION`과 분리해 명시한다.
3. retention 기간과 저장 위치를 문서화한다.
4. request id 기준 조회 범위를 local admin 또는 internal diagnostic으로 제한한다.
5. write tool audit은 admin auth/policy와 같은 loop에서 설계한다.

## Public Response Policy

Public `/agent/*` API를 열 경우 기본 응답에는 아래만 포함한다:

- `request_id`
- `ok`
- `tool.name`
- `outcome.error.code`
- `middleware.blocked_by`
- `runtime.elapsed_ms`

아래는 public response 기본값에서 제외한다:

- raw user input
- raw payload
- retrieved context
- document content
- local path
- upload/admin free-text
- full middleware detail
- full audit log

## Implementation Guidance

다음 구현 loop에서 추가할 최소 함수 후보:

- `redact_execution_trace(trace: dict[str, object], *, audience: str) -> dict[str, object]`
- audience 후보: `internal`, `public`, `persisted`
- `public`은 가장 보수적인 profile이다.
- `persisted`는 raw text와 path를 제거하고 diagnostic seed만 남긴다.
- `internal`도 credential/admin code/full content는 항상 제거한다.

## Decision

- 지금은 trace persistence를 구현하지 않는다.
- public API는 열지 않는다.
- 저장/외부 노출 전에는 이 문서 기준의 redaction function이 먼저 필요하다.
- 다음 구현 후보는 `redact_execution_trace()`의 순수 함수와 단위 테스트다.
