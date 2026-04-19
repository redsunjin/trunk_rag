from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services import runtime_service, tool_apply_service

MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION = "v1.5.mutation_executor_contract.v1"
REINDEX_LIVE_ADAPTER_OUTLINE_SCHEMA_VERSION = "v1.5.reindex_live_adapter_outline.v1"
REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION = "v1.5.reindex_live_adapter_result.v1"
REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION = "v1.5.reindex_live_adapter_error.v1"
REINDEX_LIVE_ADAPTER_BINDING_SCHEMA_VERSION = "v1.5.reindex_live_adapter_binding.v1"
MUTATION_EXECUTION_ENV_KEY = "DOC_RAG_AGENT_MUTATION_EXECUTION"
REINDEX_MUTATION_EXECUTOR_NAME = "reindex_mutation_adapter_stub"
REINDEX_LIVE_ADAPTER_EXECUTOR_NAME = "reindex_mutation_adapter_live"
NOOP_MUTATION_EXECUTOR_NAME = "noop_mutation_executor"
REINDEX_FIRST_LIVE_SCOPE = "reindex"
LOCAL_FILE_APPEND_ONLY_SINK_TYPE = "local_file_append_only"
APPROVE_UPLOAD_REQUEST_TOOL = "approve_upload_request"
REJECT_UPLOAD_REQUEST_TOOL = "reject_upload_request"
UPLOAD_REVIEW_MUTATION_TOOLS = frozenset({APPROVE_UPLOAD_REQUEST_TOOL, REJECT_UPLOAD_REQUEST_TOOL})


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


def _build_boundary_contract(request: MutationExecutionRequest) -> dict[str, object]:
    if request.tool_name == REINDEX_FIRST_LIVE_SCOPE:
        return {
            "family": "reindex",
            "classification": "derivative_runtime_state",
            "live_candidate_allowed": True,
            "managed_state_write": False,
            "approval_state_write": False,
            "requires_durable_audit_receipt": True,
            "requires_rollback_plan": False,
            "requires_managed_state_snapshot": False,
            "requires_document_version_binding": False,
            "requires_decision_audit": False,
            "required_preconditions": ["operator_activation", "durable_audit_ready"],
            "blocked_by": [],
            "live_adapter_outline": {
                "schema_version": REINDEX_LIVE_ADAPTER_OUTLINE_SCHEMA_VERSION,
                "status": "outline_only_deferred",
                "target_executor_name": REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                "current_executor_name": REINDEX_MUTATION_EXECUTOR_NAME,
                "handoff_from_selection_state": "candidate_stub",
                "execution_mode": "off_by_default",
                "required_inputs": [
                    "payload.collection",
                    "preview_seed.target.collection_key",
                    "apply_envelope.preview_ref",
                    "apply_envelope.intent.summary",
                    "persisted_audit_record.request_id",
                    "audit_sink_receipt.sequence_id",
                ],
                "expected_outputs": [
                    "result.reindex_summary",
                    "result.audit_receipt_ref",
                    "result.rollback_hint",
                ],
                "success_contract": {
                    "schema_version": REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION,
                    "status": "succeeded",
                    "required_fields": [
                        "result.reindex_summary.collection_key",
                        "result.reindex_summary.operation",
                        "result.reindex_summary.source_basis",
                        "result.audit_receipt_ref.sequence_id",
                        "result.rollback_hint.mode",
                    ],
                    "reindex_summary": {
                        "operation": "rebuild_vector_index",
                        "source_basis": "source_documents_snapshot",
                        "reset_allowed": True,
                        "compatibility_bundle_optional": True,
                    },
                    "audit_receipt_ref": {
                        "source": "append_only_receipt",
                        "sequence_id_required": True,
                        "storage_path_required": True,
                    },
                    "rollback_hint": {
                        "mode": "rebuild_from_source_documents",
                        "operator_action_required": True,
                    },
                },
                "failure_taxonomy": {
                    "schema_version": REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
                    "codes": [
                        {
                            "code": "REINDEX_TARGET_MISMATCH",
                            "stage": "contract_validation",
                            "retryable": False,
                        },
                        {
                            "code": "REINDEX_AUDIT_LINKAGE_INVALID",
                            "stage": "audit_linkage",
                            "retryable": False,
                        },
                        {
                            "code": "REINDEX_RUNTIME_EXECUTION_FAILED",
                            "stage": "executor_runtime",
                            "retryable": True,
                        },
                        {
                            "code": "REINDEX_ROLLBACK_HINT_UNAVAILABLE",
                            "stage": "post_execution",
                            "retryable": True,
                        },
                    ],
                },
                "opt_in_binding": {
                    "schema_version": REINDEX_LIVE_ADAPTER_BINDING_SCHEMA_VERSION,
                    "mode": "explicit_local_only",
                    "binding_source": "runtime_injected_executor_binding",
                    "binding_owner": "local_operator_or_test_harness",
                    "default_executor_name": REINDEX_MUTATION_EXECUTOR_NAME,
                    "opt_in_executor_name": REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                    "selection_precedence": [
                        "tool_registration_boundary",
                        "activation_guard",
                        "candidate_stub_default",
                        "explicit_live_binding_override",
                    ],
                    "required_signals": [
                        "activation_requested",
                        "durable_audit_ready",
                        "explicit_live_adapter_binding",
                    ],
                    "public_surface_allowed": False,
                    "shared_with_upload_review": False,
                },
                "rollback_awareness": {
                    "mode": "rebuild_from_source_documents",
                    "managed_state_rollback_required": False,
                    "operator_restore_hint_required": True,
                },
                "test_seams": [
                    "noop_fallback_contract",
                    "candidate_stub_contract",
                    "future_live_adapter_opt_in_smoke",
                ],
                "non_goals": [
                    "managed_state_write_rollback",
                    "upload_review_execution",
                    "public_agent_endpoint",
                ],
            },
        }
    if request.tool_name == APPROVE_UPLOAD_REQUEST_TOOL:
        return {
            "family": "upload_review",
            "classification": "managed_doc_activation",
            "live_candidate_allowed": False,
            "managed_state_write": True,
            "approval_state_write": True,
            "requires_durable_audit_receipt": True,
            "requires_rollback_plan": True,
            "requires_managed_state_snapshot": True,
            "requires_document_version_binding": True,
            "requires_decision_audit": True,
            "required_preconditions": [
                "separate_upload_review_go_no_go",
                "decision_audit_contract",
                "managed_state_snapshot",
                "document_version_binding",
                "rollback_plan",
            ],
            "blocked_by": [
                "upload_review_scope_deferred",
                "managed_state_rollback_not_ready",
                "document_version_binding_not_reviewed",
            ],
        }
    if request.tool_name == REJECT_UPLOAD_REQUEST_TOOL:
        return {
            "family": "upload_review",
            "classification": "request_decision_only",
            "live_candidate_allowed": False,
            "managed_state_write": False,
            "approval_state_write": True,
            "requires_durable_audit_receipt": True,
            "requires_rollback_plan": False,
            "requires_managed_state_snapshot": False,
            "requires_document_version_binding": False,
            "requires_decision_audit": True,
            "required_preconditions": [
                "separate_upload_review_go_no_go",
                "decision_audit_contract",
            ],
            "blocked_by": [
                "upload_review_scope_deferred",
                "decision_audit_contract_not_reviewed",
            ],
        }
    return {
        "family": "unregistered_mutation",
        "classification": "no_registered_boundary",
        "live_candidate_allowed": False,
        "managed_state_write": False,
        "approval_state_write": False,
        "requires_durable_audit_receipt": False,
        "requires_rollback_plan": False,
        "requires_managed_state_snapshot": False,
        "requires_document_version_binding": False,
        "requires_decision_audit": False,
        "required_preconditions": [],
        "blocked_by": ["tool_not_registered"],
    }


def _build_executor_contract(
    *,
    request: MutationExecutionRequest,
    executor_name: str,
    binding_kind: str,
    tool_registered: bool,
    execution_enabled: bool,
    activation_contract: dict[str, object],
    boundary_contract: dict[str, object],
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
        "boundary": dict(boundary_contract),
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
    boundary_contract: dict[str, object] | None = None
    registered_executor_name: str | None = None

    def supports(self, tool_name: str) -> bool:
        return True

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
        activation_contract = dict(self.activation_contract) if isinstance(self.activation_contract, dict) else _build_activation_contract(request)
        boundary_contract = dict(self.boundary_contract) if isinstance(self.boundary_contract, dict) else _build_boundary_contract(request)
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
                boundary_contract=boundary_contract,
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
    boundary_contract: dict[str, object] | None = None

    def supports(self, tool_name: str) -> bool:
        return tool_name == "reindex"

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
        activation_contract = dict(self.activation_contract) if isinstance(self.activation_contract, dict) else _build_activation_contract(request)
        boundary_contract = dict(self.boundary_contract) if isinstance(self.boundary_contract, dict) else _build_boundary_contract(request)
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
                boundary_contract=boundary_contract,
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
    boundary_contract = _build_boundary_contract(request)
    if request.tool_name in UPLOAD_REVIEW_MUTATION_TOOLS:
        return NoopMutationExecutor(
            selection_state="boundary_noop",
            selection_reason="upload_review_scope_deferred",
            activation_contract=activation_contract,
            boundary_contract=boundary_contract,
        )
    if request.tool_name != REINDEX_FIRST_LIVE_SCOPE:
        return NoopMutationExecutor(
            activation_contract=activation_contract,
            boundary_contract=boundary_contract,
        )
    if list(activation_contract.get("blocked_by") or []):
        return NoopMutationExecutor(
            tool_registered=True,
            selection_state="noop_fallback",
            selection_reason="activation_guard_blocked",
            activation_contract=activation_contract,
            boundary_contract=boundary_contract,
            registered_executor_name=REINDEX_MUTATION_EXECUTOR_NAME,
        )
    return ReindexMutationExecutorAdapter(
        activation_contract=activation_contract,
        boundary_contract=boundary_contract,
    )


def execute_mutation_request(request: MutationExecutionRequest) -> dict[str, object]:
    executor = resolve_mutation_executor(request)
    return executor.execute(request)
