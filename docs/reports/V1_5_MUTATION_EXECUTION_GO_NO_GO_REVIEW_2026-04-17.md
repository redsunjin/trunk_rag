# V1.5 Mutation Execution Go/No-Go Review - 2026-04-17

## Scope

- 대상 루프: `LOOP-034 V1.5 mutation execution go/no-go review`
- 기준 상태: `LOOP-033` mutation apply guard skeleton 반영 이후
- 목적: 실제 write execution을 열기 전에 필요한 go/no-go 기준, backend/retention 전제조건, activation ownership, public surface 경계를 문서로 고정한다.

## Current Baseline

현재 내부 runtime은 아래 수준까지 준비돼 있다.

- `services/tool_middleware_service.py`의 `mutation_policy_guard`는 mutation candidate write를 `ADMIN_AUTH_REQUIRED` -> `MUTATION_INTENT_REQUIRED` -> `PREVIEW_REQUIRED` 순서로 차단한다.
- `services/tool_middleware_service.py`의 `mutation_apply_guard`는 preview-confirmed `apply_envelope`를 검증하지만, valid envelope도 최종적으로 `MUTATION_APPLY_NOT_ENABLED`로 막아 둔다.
- `services/tool_trace_service.py`는 `v1.5.mutation_audit_record.v1` 기준 persisted audit record를 만들고, `services/tool_audit_sink_service.py`는 `null_append_only`, `memory_append_only` sink만 제공한다.
- `services/tool_apply_service.py`는 preview reference, audit receipt, intent summary가 맞는지 검증하는 handshake까지 제공하지만 실제 executor는 없다.
- 현재 mutation candidate tool은 `reindex`, `approve_upload_request`, `reject_upload_request`다.
- `reindex`는 파생 index/vector 상태를 다시 만들고, upload review 계열은 `chroma_db/managed_docs/` 아래 active markdown 원본을 바꾸므로 같은 write여도 위험도가 다르다.
- public `/agent/*` endpoint는 여전히 없고, internal single-tool runtime만 존재한다.

## Decision

2026-04-17 기준 결론은 `No-Go`다.

- 실제 mutation execution은 아직 열지 않는다.
- `LOOP-035`에서는 live adapter를 붙이지 않고 executor interface와 noop/default adapter 경계만 정의한다.
- 이후 activation 검토가 다시 필요하더라도 첫 live 범위는 모든 write tool이 아니라 `reindex` 단일 tool부터 다시 판단한다.

## Why No-Go

1. durable audit backend가 없다.
   - 현재 receipt는 `null_append_only` 또는 테스트용 `memory_append_only` 기준이라, 실제 운영 감사 기록을 남겼다고 보기 어렵다.
2. retention과 prune 책임이 없다.
   - persisted record schema는 정해졌지만 보존 기간, 삭제 시점, 운영자가 어떤 방식으로 비우는지 아직 없다.
3. activation ownership이 문서화되지 않았다.
   - 코드가 머지됐다는 이유만으로 write execution이 자동 개방되면 `V1` 안정 기준과 충돌한다.
4. write tool의 위험도가 서로 다르다.
   - `reindex`는 파생 상태 재구성이지만 upload review는 managed markdown active 상태를 직접 바꾼다.
   - 첫 activation에서 두 부류를 같은 adapter 정책으로 묶는 것은 과도하다.
5. public/internal surface가 아직 없다.
   - 현재는 internal runtime만 있으므로, execution activation은 내부 service 경계 안에서만 다뤄야 한다.

## Decision Matrix

| topic | options considered | selected direction | rationale | follow-up |
| --- | --- | --- | --- | --- |
| execution activation | valid `apply_envelope` 즉시 실행 / explicit operator gate 뒤 실행 / public API와 함께 실행 | explicit operator gate 뒤 실행, 기본값 `off` | merge만으로 write capability가 열리면 안 된다. | `LOOP-035`에서 env/config 기반 activation seam만 정의 |
| audit backend | `null`/memory sink 유지 / local append-only file / external DB | local append-only file | 현재 제품은 local-first이고 새 인프라 의존성 없이 durable receipt를 만들 수 있다. | 권장 경로는 `chroma_db/mutation_audit/` 아래 append-only JSONL rotation |
| retention | 무기한 보관 / 짧은 rolling retention / 수동 삭제만 허용 | `90일 rolling retention` + 명시적 prune | 로컬 운영 감사에는 충분하고 용량 증가를 통제할 수 있다. | prune 규칙과 운영 문구를 activation 전 문서/스크립트로 고정 |
| activation ownership | 코드 머지 시 자동 / 요청 payload flag / 로컬 operator 설정 | 로컬 operator 설정 | 실행 권한은 코드 작성자가 아니라 운영자가 열어야 한다. | 예: `DOC_RAG_AGENT_MUTATION_EXECUTION=1` 같은 명시적 로컬 설정 |
| public surface | public `/agent/*` / admin-only HTTP / internal service only | internal service only | answer/auth/rate-limit 계약이 아직 없다. | public surface는 별도 loop에서만 재검토 |
| first live tool scope | 모든 write tool 동시 / `reindex` 먼저 / upload review 먼저 | `reindex` 먼저 | 파생 상태 재구성이 managed markdown 변경보다 되돌리기 쉽다. | upload review execution은 별도 go/no-go로 분리 |
| executor shape | tool handler 직접 호출 / generic executor protocol + per-tool adapter / workflow engine | generic executor protocol + per-tool adapter + noop default | 현재 off-by-default 상태를 깨지 않고 테스트 가능한 seam을 만들 수 있다. | `LOOP-035` 구현 대상 |

## Activation Preconditions

아래 조건이 모두 충족되기 전까지 `MUTATION_APPLY_NOT_ENABLED`를 유지한다.

1. durable append-only backend가 실제 sequence id를 반환한다.
2. retention 기간과 prune 책임이 문서/운영 스크립트로 고정된다.
3. activation은 local operator explicit config로만 열 수 있다.
4. execution path는 internal runtime 경계에만 남고 public `/agent/*`와 분리된다.
5. executor interface가 `noop default`와 live adapter를 분리한다.
6. 첫 live scope는 `reindex` 단일 tool로 제한한다.
7. preview -> apply -> execution -> persisted audit 흐름에 대한 targeted test/smoke가 추가된다.

## LOOP-035 Input Contract

`LOOP-035 V1.5 mutation executor interface draft`는 아래만 다룬다.

- `MutationExecutionRequest`
  - validated `apply_envelope`
  - current `preview_seed`
  - persisted audit record + durable receipt
  - tool payload/context seed
- `MutationExecutor` protocol
  - `supports(tool_name)`
  - `execute(request)`
- `NoopMutationExecutor`
  - 기본 executor
  - activation이 꺼져 있거나 tool adapter가 없을 때만 사용
- tool adapter registry
  - `reindex` 후보를 우선 고려
  - upload review 계열은 interface registry에 이름만 올릴 수 있어도 live adapter는 이번 단계 제외

이번 loop에서 의도적으로 하지 않는 것:

- 실제 write execution 활성화
- durable backend 구현
- retention prune 스크립트 구현
- public `/agent/*` endpoint 추가
- upload review live automation 개방

## Operational Notes

- append-only audit 위치는 vector/index reset과 분리된 책임으로 다루되, 현재 로컬 런타임 관례를 따라 ignored runtime tree 안에 둔다.
- preview/apply handshake는 계속 동일 schema(`preview_seed`, `apply_envelope`, persisted audit record)를 재사용하고, executor layer는 그 아래에서만 동작한다.
- upload review execution은 active markdown 원본과 승인 상태를 함께 바꾸므로 `reindex`보다 강한 rollback/operational policy가 필요하다.

## Validation

- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Next Step

다음 loop는 `LOOP-035 V1.5 mutation executor interface draft`다. 이 단계에서는 실제 write를 열지 않고, `NoopMutationExecutor` 기본값과 tool별 adapter seam을 문서/테스트 기준으로 고정한다.
