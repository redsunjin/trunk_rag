from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services import runtime_service, tool_apply_service

MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION = "v1.5.mutation_executor_contract.v1"
MUTATION_EXECUTION_ENV_KEY = "DOC_RAG_AGENT_MUTATION_EXECUTION"


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


def _build_executor_contract(
    *,
    request: MutationExecutionRequest,
    executor_name: str,
    binding_kind: str,
    tool_registered: bool,
    execution_enabled: bool,
    delegate_executor_name: str | None = None,
) -> dict[str, object]:
    contract = {
        "schema_version": MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": executor_name,
        "binding_kind": binding_kind,
        "tool_name": request.tool_name,
        "tool_registered": tool_registered,
        "activation_requested": is_mutation_execution_requested(),
        "execution_enabled": execution_enabled,
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
    executor_name: str = "noop_mutation_executor"
    binding_kind: str = "default_noop"

    def supports(self, tool_name: str) -> bool:
        return True

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
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
                tool_registered=False,
                execution_enabled=False,
            ),
        }


@dataclass(frozen=True)
class ReindexMutationExecutorAdapter:
    executor_name: str = "reindex_mutation_adapter_stub"
    binding_kind: str = "tool_adapter_stub"

    def supports(self, tool_name: str) -> bool:
        return tool_name == "reindex"

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
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
                delegate_executor_name="noop_mutation_executor",
            ),
        }


def list_registered_mutation_executor_bindings() -> dict[str, str]:
    return {
        "reindex": "reindex_mutation_adapter_stub",
    }


def resolve_mutation_executor(tool_name: str) -> MutationExecutor:
    if tool_name == "reindex":
        return ReindexMutationExecutorAdapter()
    return NoopMutationExecutor()


def execute_mutation_request(request: MutationExecutionRequest) -> dict[str, object]:
    executor = resolve_mutation_executor(request.tool_name)
    return executor.execute(request)
