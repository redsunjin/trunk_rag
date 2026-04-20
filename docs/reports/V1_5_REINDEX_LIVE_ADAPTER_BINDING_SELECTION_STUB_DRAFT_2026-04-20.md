# V1.5 Reindex Live Adapter Binding Selection Stub Draft (2026-04-20)

## 목적
- explicit local-only binding이 주입된 경우 `reindex_mutation_adapter_live`로 selection state를 전환하는 safe stub를 추가한다.

## Binding Contract
- required fields
  - `binding_kind=explicit_live_adapter`
  - `binding_source=<local runtime or harness label>`
  - `executor_name=reindex_mutation_adapter_live`
- invalid binding behavior
  - `candidate_stub_fallback`

## Selection Rules
- `activation_guard_blocked`
  - binding이 있어도 `noop_fallback`
- `activation_guard_satisfied` + valid binding
  - `executor_name=reindex_mutation_adapter_live`
  - `selection_state=live_binding_stub`
  - `selection_reason=explicit_live_binding_requested`
- `activation_guard_satisfied` + no/invalid binding
  - 기존 `reindex_mutation_adapter_stub` 유지

## Stub Semantics
- 현재 live binding stub도 실제 execution은 열지 않는다.
- 결과는 계속 `MUTATION_APPLY_NOT_ENABLED`다.
- contract에는 `registered_executor_name=reindex_mutation_adapter_stub`, `delegate_executor_name=noop_mutation_executor`를 남겨 현재 defer 상태를 드러낸다.

## 코드 반영
- `services/mutation_executor_service.py`
  - `REINDEX_LIVE_ADAPTER_BINDING_KIND`
  - `_resolve_reindex_live_binding()`
  - `ReindexLiveMutationExecutorBindingStub`

## 검증
- unit
  - valid binding -> `live_binding_stub`
  - invalid binding -> `candidate_stub`
- integration
  - middleware/apply path에서 injected binding이 live stub selection으로 이어지는지 확인
