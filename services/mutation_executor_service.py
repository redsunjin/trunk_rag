from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services import runtime_service, tool_apply_service

MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION = "v1.5.mutation_executor_contract.v1"
MUTATION_EXECUTION_ENV_KEY = "DOC_RAG_AGENT_MUTATION_EXECUTION"
REINDEX_MUTATION_EXECUTOR_NAME = "reindex_mutation_adapter_stub"
NOOP_MUTATION_EXECUTOR_NAME = "noop_mutation_executor"
REINDEX_FIRST_LIVE_SCOPE = "reindex"
LOCAL_FILE_APPEND_ONLY_SINK_TYPE = "local_file_append_only"


@dataclass(frozen=True)
class MutationExecutionRequest:
    request_id: str
    tool_name: str
    payload: dict[str, object]
    apply_envelope: dict[str, object]
    preview_seed: dict[str, object]
    persisted_audit_record: dict[str, object]
    audit_sink_receipt: dict[str, object]
    actor: str
    actor_category: str | None
    allow_mutation: bool
    timeout_seconds: float | None


class MutationExecutor(Protocol):
    executor_name: str
    binding_kind: str

    def supports(self, tool_name: str) -> bool:
        ...

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
        ...


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _safe_positive_int(value: object) -> int | None:
    try:
        normalized = int(value)
    except (TypeError, ValueError):
        return None
    if normalized <= 0:
        return None
    return normalized


def _build_activation_contract(request: MutationExecutionRequest) -> dict[str, object]:
    activation_requested = is_mutation_execution_requested()
    audit_sink_receipt = _safe_dict(request.audit_sink_receipt)
    audit_sink_type = _normalize_optional_text(audit_sink_receipt.get("sink_type"))
    audit_sequence_id = _safe_positive_int(audit_sink_receipt.get("sequence_id"))
    audit_storage_path = _normalize_optional_text(audit_sink_receipt.get("storage_path"))
    durable_audit_required = request.tool_name == REINDEX_FIRST_LIVE_SCOPE
    durable_audit_ready = False
    blocked_by: list[str] = []
    if durable_audit_required:
        durable_audit_ready = (
            audit_sink_type == LOCAL_FILE_APPEND_ONLY_SINK_TYPE
            and audit_sequence_id is not None
            and audit_storage_path is not None
        )
        if not activation_requested:
            blocked_by.append("activation_not_requested")
        if not durable_audit_ready:
            blocked_by.append("durable_audit_not_ready")
    return {
        "surface_scope": "internal_service_only",
        "activation_source": "local_env_flag",
        "ownership": "operator_local_config",
        "env_key": MUTATION_EXECUTION_ENV_KEY,
        "requested": activation_requested,
        "first_live_tool_scope": REINDEX_FIRST_LIVE_SCOPE,
        "durable_audit_required": durable_audit_required,
        "durable_audit_ready": durable_audit_ready,
        "audit_sink_type": audit_sink_type,
        "audit_sequence_id": audit_sequence_id,
        "audit_storage_path": audit_storage_path,
        "blocked_by": blocked_by,
    }


def _build_executor_contract(
    *,
    request: MutationExecutionRequest,
    executor_name: str,
    binding_kind: str,
    tool_registered: bool,
    execution_enabled: bool,
    activation_contract: dict[str, object],
    selection_state: str,
    selection_reason: str,
    registered_executor_name: str | None = None,
    delegate_executor_name: str | None = None,
) -> dict[str, object]:
    contract = {
        "schema_version": MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": executor_name,
        "binding_kind": binding_kind,
        "tool_name": request.tool_name,
        "tool_registered": tool_registered,
        "activation_requested": bool(activation_contract.get("requested")),
        "execution_enabled": execution_enabled,
        "selection_state": selection_state,
        "selection_reason": selection_reason,
        "activation": dict(activation_contract),
        "request": {
            "request_id": request.request_id,
            "actor_category": request.actor_category,
            "allow_mutation": request.allow_mutation,
            "timeout_seconds": request.timeout_seconds,
            "apply_schema_version": _safe_dict(request.apply_envelope).get("schema_version"),
            "preview_schema_version": _safe_dict(request.preview_seed).get("schema_version"),
            "audit_record_schema_version": _safe_dict(request.persisted_audit_record).get("schema_version"),
            "audit_sink_type": _safe_dict(request.audit_sink_receipt).get("sink_type"),
        },
    }
    if registered_executor_name:
        contract["registered_executor_name"] = registered_executor_name
    if delegate_executor_name:
        contract["delegate_executor_name"] = delegate_executor_name
    return contract


def build_mutation_execution_request(
    *,
    request_id: str,
    tool_name: str,
    payload: dict[str, object] | None,
    apply_envelope: dict[str, object] | None,
    preview_seed: dict[str, object] | None,
    persisted_audit_record: dict[str, object] | None,
    audit_sink_receipt: dict[str, object] | None,
    actor: str,
    actor_category: str | None,
    allow_mutation: bool,
    timeout_seconds: float | None,
) -> MutationExecutionRequest | None:
    if not (
        isinstance(payload, dict)
        and isinstance(apply_envelope, dict)
        and isinstance(preview_seed, dict)
        and isinstance(persisted_audit_record, dict)
        and isinstance(audit_sink_receipt, dict)
    ):
        return None
    return MutationExecutionRequest(
        request_id=request_id,
        tool_name=tool_name,
        payload=dict(payload),
        apply_envelope=dict(apply_envelope),
        preview_seed=dict(preview_seed),
        persisted_audit_record=dict(persisted_audit_record),
        audit_sink_receipt=dict(audit_sink_receipt),
        actor=actor,
        actor_category=actor_category,
        allow_mutation=allow_mutation,
        timeout_seconds=timeout_seconds,
    )


def is_mutation_execution_requested() -> bool:
    return runtime_service.parse_bool_env(MUTATION_EXECUTION_ENV_KEY, default=False)


@dataclass(frozen=True)
class NoopMutationExecutor:
    executor_name: str = NOOP_MUTATION_EXECUTOR_NAME
    binding_kind: str = "default_noop"
    tool_registered: bool = False
    selection_state: str = "default_noop"
    selection_reason: str = "tool_not_registered"
    activation_contract: dict[str, object] | None = None
    registered_executor_name: str | None = None

    def supports(self, tool_name: str) -> bool:
        return True

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
        activation_contract = dict(self.activation_contract) if isinstance(self.activation_contract, dict) else _build_activation_contract(request)
        return {
            "ok": False,
            "error": {
                "code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
                "message": "Mutation apply handshake validated, but execution is not enabled yet.",
            },
            "executor": _build_executor_contract(
                request=request,
                executor_name=self.executor_name,
                binding_kind=self.binding_kind,
                tool_registered=self.tool_registered,
                execution_enabled=False,
                activation_contract=activation_contract,
                selection_state=self.selection_state,
                selection_reason=self.selection_reason,
                registered_executor_name=self.registered_executor_name,
            ),
        }


@dataclass(frozen=True)
class ReindexMutationExecutorAdapter:
    executor_name: str = REINDEX_MUTATION_EXECUTOR_NAME
    binding_kind: str = "tool_adapter_stub"
    selection_state: str = "candidate_stub"
    selection_reason: str = "activation_guard_satisfied"
    activation_contract: dict[str, object] | None = None

    def supports(self, tool_name: str) -> bool:
        return tool_name == "reindex"

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
        activation_contract = dict(self.activation_contract) if isinstance(self.activation_contract, dict) else _build_activation_contract(request)
        return {
            "ok": False,
            "error": {
                "code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
                "message": "Mutation apply handshake validated, but execution is not enabled yet.",
            },
            "executor": _build_executor_contract(
                request=request,
                executor_name=self.executor_name,
                binding_kind=self.binding_kind,
                tool_registered=True,
                execution_enabled=False,
                activation_contract=activation_contract,
                selection_state=self.selection_state,
                selection_reason=self.selection_reason,
                delegate_executor_name=NOOP_MUTATION_EXECUTOR_NAME,
            ),
        }


def list_registered_mutation_executor_bindings() -> dict[str, str]:
    return {
        "reindex": REINDEX_MUTATION_EXECUTOR_NAME,
    }


def resolve_mutation_executor(request: MutationExecutionRequest) -> MutationExecutor:
    activation_contract = _build_activation_contract(request)
    if request.tool_name != REINDEX_FIRST_LIVE_SCOPE:
        return NoopMutationExecutor(activation_contract=activation_contract)
    if list(activation_contract.get("blocked_by") or []):
        return NoopMutationExecutor(
            tool_registered=True,
            selection_state="noop_fallback",
            selection_reason="activation_guard_blocked",
            activation_contract=activation_contract,
            registered_executor_name=REINDEX_MUTATION_EXECUTOR_NAME,
        )
    return ReindexMutationExecutorAdapter(activation_contract=activation_contract)


def execute_mutation_request(request: MutationExecutionRequest) -> dict[str, object]:
    executor = resolve_mutation_executor(request)
    return executor.execute(request)
