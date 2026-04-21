from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from services import runtime_service, tool_apply_service

MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION = "v1.5.mutation_executor_contract.v1"
REINDEX_LIVE_ADAPTER_OUTLINE_SCHEMA_VERSION = "v1.5.reindex_live_adapter_outline.v1"
REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION = "v1.5.reindex_live_adapter_result.v1"
REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION = "v1.5.reindex_live_adapter_error.v1"
REINDEX_LIVE_ADAPTER_BINDING_SCHEMA_VERSION = "v1.5.reindex_live_adapter_binding.v1"
REINDEX_LIVE_ADAPTER_INJECTION_PROTOCOL_SCHEMA_VERSION = "v1.5.reindex_live_adapter_injection_protocol.v1"
REINDEX_LIVE_ADAPTER_SMOKE_HARNESS_SCHEMA_VERSION = "v1.5.reindex_live_adapter_smoke_harness.v1"
REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_SCHEMA_VERSION = "v1.5.reindex_live_adapter_success_promotion.v1"
MUTATION_EXECUTION_ENV_KEY = "DOC_RAG_AGENT_MUTATION_EXECUTION"
REINDEX_MUTATION_EXECUTOR_NAME = "reindex_mutation_adapter_stub"
REINDEX_LIVE_ADAPTER_EXECUTOR_NAME = "reindex_mutation_adapter_live"
REINDEX_LIVE_ADAPTER_BINDING_KIND = "explicit_live_adapter"
REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD = "binding_stage"
REINDEX_LIVE_ADAPTER_BINDING_STAGE_SELECTION_STUB = "selection_stub"
REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON = "concrete_executor_skeleton"
NOOP_MUTATION_EXECUTOR_NAME = "noop_mutation_executor"
REINDEX_FIRST_LIVE_SCOPE = "reindex"
LOCAL_FILE_APPEND_ONLY_SINK_TYPE = "local_file_append_only"
APPROVE_UPLOAD_REQUEST_TOOL = "approve_upload_request"
REJECT_UPLOAD_REQUEST_TOOL = "reject_upload_request"
UPLOAD_REVIEW_MUTATION_TOOLS = frozenset({APPROVE_UPLOAD_REQUEST_TOOL, REJECT_UPLOAD_REQUEST_TOOL})
REINDEX_ERROR_TARGET_MISMATCH = "REINDEX_TARGET_MISMATCH"
REINDEX_ERROR_AUDIT_LINKAGE_INVALID = "REINDEX_AUDIT_LINKAGE_INVALID"
REINDEX_ERROR_RUNTIME_EXECUTION_FAILED = "REINDEX_RUNTIME_EXECUTION_FAILED"
REINDEX_ERROR_ROLLBACK_HINT_UNAVAILABLE = "REINDEX_ROLLBACK_HINT_UNAVAILABLE"
REINDEX_LIVE_ADAPTER_FAILURE_ORDER = (
    REINDEX_ERROR_TARGET_MISMATCH,
    REINDEX_ERROR_AUDIT_LINKAGE_INVALID,
    REINDEX_ERROR_RUNTIME_EXECUTION_FAILED,
    REINDEX_ERROR_ROLLBACK_HINT_UNAVAILABLE,
)
REINDEX_LIVE_ADAPTER_FAILURE_TAXONOMY = {
    REINDEX_ERROR_TARGET_MISMATCH: {
        "stage": "contract_validation",
        "retryable": False,
        "trigger": "payload_apply_preview_target_mismatch",
        "message": "Reindex target fields do not agree across payload, preview, and apply envelope.",
    },
    REINDEX_ERROR_AUDIT_LINKAGE_INVALID: {
        "stage": "audit_linkage",
        "retryable": False,
        "trigger": "append_only_receipt_unlinkable",
        "message": "Append-only audit receipt cannot be linked to the reindex adapter result.",
    },
    REINDEX_ERROR_RUNTIME_EXECUTION_FAILED: {
        "stage": "executor_runtime",
        "retryable": True,
        "trigger": "reindex_runtime_failed",
        "message": "Reindex runtime execution failed after the adapter contract was accepted.",
    },
    REINDEX_ERROR_ROLLBACK_HINT_UNAVAILABLE: {
        "stage": "post_execution",
        "retryable": True,
        "trigger": "operator_restore_hint_missing",
        "message": "Reindex finished or partially finished, but an operator restore hint was not available.",
    },
}


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
    executor_binding: dict[str, object] | None = None


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


def _build_reindex_failure_taxonomy() -> dict[str, object]:
    return {
        "schema_version": REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
        "codes": [
            {
                "code": code,
                "stage": str(REINDEX_LIVE_ADAPTER_FAILURE_TAXONOMY[code]["stage"]),
                "retryable": bool(REINDEX_LIVE_ADAPTER_FAILURE_TAXONOMY[code]["retryable"]),
            }
            for code in REINDEX_LIVE_ADAPTER_FAILURE_ORDER
        ],
    }


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
                "failure_taxonomy": _build_reindex_failure_taxonomy(),
                "opt_in_binding": {
                    "schema_version": REINDEX_LIVE_ADAPTER_BINDING_SCHEMA_VERSION,
                    "mode": "explicit_local_only",
                    "binding_source": "runtime_injected_executor_binding",
                    "binding_owner": "local_operator_or_test_harness",
                    "default_executor_name": REINDEX_MUTATION_EXECUTOR_NAME,
                    "opt_in_executor_name": REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                    "binding_kind": REINDEX_LIVE_ADAPTER_BINDING_KIND,
                    "binding_contract_fields": [
                        "binding_kind",
                        "binding_source",
                        "executor_name",
                        REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD,
                    ],
                    "binding_stage_field": REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD,
                    "default_binding_stage": REINDEX_LIVE_ADAPTER_BINDING_STAGE_SELECTION_STUB,
                    "concrete_executor_stage": REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON,
                    "selection_precedence": [
                        "tool_registration_boundary",
                        "activation_guard",
                        "candidate_stub_default",
                        "explicit_live_binding_override",
                    ],
                    "invalid_binding_behavior": "candidate_stub_fallback",
                    "live_selection_state": "live_binding_stub",
                    "required_signals": [
                        "activation_requested",
                        "durable_audit_ready",
                        "explicit_live_adapter_binding",
                    ],
                    "public_surface_allowed": False,
                    "shared_with_upload_review": False,
                },
                "executor_injection_protocol": {
                    "schema_version": REINDEX_LIVE_ADAPTER_INJECTION_PROTOCOL_SCHEMA_VERSION,
                    "mode": "request_scoped_local_only",
                    "carrier_chain": [
                        "agent_runtime_request.executor_binding",
                        "tool_context.executor_binding",
                        "mutation_execution_request.executor_binding",
                    ],
                    "direct_entrypoints": [
                        "agent_runtime_service.run_agent_entry",
                        "tool_middleware_service.invoke_tool_with_middlewares",
                        "mutation_executor_service.build_mutation_execution_request",
                    ],
                    "payload_channel_allowed": False,
                    "binding_owner": "local_runtime_or_test_harness",
                    "default_behavior": "absent_binding_keeps_candidate_stub",
                    "contract_signal_fields": [
                        "request.executor_binding_present",
                        "request.executor_binding_kind",
                        "request.executor_binding_source",
                        "request.executor_binding_executor_name",
                    ],
                    "required_guards": [
                        "activation_requested",
                        "durable_audit_ready",
                        "explicit_live_adapter_binding",
                    ],
                },
                "opt_in_smoke_harness": {
                    "schema_version": REINDEX_LIVE_ADAPTER_SMOKE_HARNESS_SCHEMA_VERSION,
                    "mode": "separate_from_default_smoke",
                    "default_command": "./.venv/bin/python scripts/smoke_agent_runtime.py",
                    "future_command_kind": "explicit_live_adapter_binding_required",
                    "prerequisites": [
                        "activation_requested",
                        "durable_audit_ready",
                        "explicit_live_adapter_binding",
                        "local_only_runtime_context",
                    ],
                    "expected_evidence": [
                        "result.ok=true",
                        "result.mutation_executor.executor_name=reindex_mutation_adapter_live",
                        "result.result.reindex_summary",
                        "result.result.audit_receipt_ref",
                        "result.result.rollback_hint",
                    ],
                    "isolation": {
                        "shares_default_smoke_suite": False,
                        "upload_review_included": False,
                        "public_surface_allowed": False,
                    },
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
    executor_binding = _safe_dict(request.executor_binding)
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
            "executor_binding_present": bool(executor_binding),
            "executor_binding_kind": _normalize_optional_text(executor_binding.get("binding_kind")),
            "executor_binding_source": _normalize_optional_text(executor_binding.get("binding_source")),
            "executor_binding_executor_name": _normalize_optional_text(executor_binding.get("executor_name")),
            "executor_binding_stage": _normalize_optional_text(executor_binding.get(REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD)),
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
    executor_binding: dict[str, object] | None = None,
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
        executor_binding=dict(executor_binding) if isinstance(executor_binding, dict) else None,
    )


def is_mutation_execution_requested() -> bool:
    return runtime_service.parse_bool_env(MUTATION_EXECUTION_ENV_KEY, default=False)


def _resolve_reindex_live_binding(request: MutationExecutionRequest) -> dict[str, str] | None:
    binding = _safe_dict(request.executor_binding)
    binding_kind = _normalize_optional_text(binding.get("binding_kind"))
    binding_source = _normalize_optional_text(binding.get("binding_source"))
    executor_name = _normalize_optional_text(binding.get("executor_name"))
    binding_stage = _normalize_optional_text(binding.get(REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD))
    if (
        binding_kind != REINDEX_LIVE_ADAPTER_BINDING_KIND
        or binding_source is None
        or executor_name != REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    ):
        return None
    return {
        "binding_kind": binding_kind,
        "binding_source": binding_source,
        "executor_name": executor_name,
        "binding_stage": binding_stage or REINDEX_LIVE_ADAPTER_BINDING_STAGE_SELECTION_STUB,
    }


def _resolve_reindex_collection_key(request: MutationExecutionRequest) -> str:
    payload_collection = _normalize_optional_text(_safe_dict(request.payload).get("collection"))
    if payload_collection is not None:
        return payload_collection
    preview_target = _safe_dict(_safe_dict(request.preview_seed).get("target"))
    preview_collection = _normalize_optional_text(preview_target.get("collection_key"))
    if preview_collection is not None:
        return preview_collection
    apply_preview_ref = _safe_dict(_safe_dict(request.apply_envelope).get("preview_ref"))
    apply_target = _safe_dict(apply_preview_ref.get("target"))
    apply_collection = _normalize_optional_text(apply_target.get("collection_key"))
    if apply_collection is not None:
        return apply_collection
    return REINDEX_FIRST_LIVE_SCOPE


def _build_reindex_live_result(request: MutationExecutionRequest) -> dict[str, object]:
    audit_sink_receipt = _safe_dict(request.audit_sink_receipt)
    collection_key = _resolve_reindex_collection_key(request)
    requested_reset = request.payload.get("reset")
    include_compatibility_bundle = request.payload.get("include_compatibility_bundle")
    return {
        "schema_version": REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION,
        "reindex_summary": {
            "collection_key": collection_key,
            "operation": "rebuild_vector_index",
            "source_basis": "source_documents_snapshot",
            "requested_reset": requested_reset is not False,
            "requested_compatibility_bundle": bool(include_compatibility_bundle),
        },
        "audit_receipt_ref": {
            "source": "append_only_receipt",
            "sequence_id": audit_sink_receipt.get("sequence_id"),
            "storage_path": audit_sink_receipt.get("storage_path"),
        },
        "rollback_hint": {
            "mode": "rebuild_from_source_documents",
            "operator_action_required": True,
            "collection_key": collection_key,
        },
    }


def build_reindex_live_success_promotion_contract(
    *,
    executor_contract: dict[str, object] | None,
    executor_result: dict[str, object] | None,
) -> dict[str, object] | None:
    executor = _safe_dict(executor_contract)
    result = _safe_dict(executor_result)
    if (
        executor.get("tool_name") != REINDEX_FIRST_LIVE_SCOPE
        or executor.get("executor_name") != REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
        or executor.get("selection_state") != "live_result_skeleton"
        or result.get("schema_version") != REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION
    ):
        return None

    reindex_summary = _safe_dict(result.get("reindex_summary"))
    audit_receipt_ref = _safe_dict(result.get("audit_receipt_ref"))
    rollback_hint = _safe_dict(result.get("rollback_hint"))
    return {
        "schema_version": REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_SCHEMA_VERSION,
        "tool_name": REINDEX_FIRST_LIVE_SCOPE,
        "promotion_state": "draft_ready_not_enabled",
        "selection_state": executor.get("selection_state"),
        "selection_reason": executor.get("selection_reason"),
        "current_surface": {
            "kind": "blocked_success_sidecar",
            "top_level_ok": False,
            "top_level_error_code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
            "result_location": "error.mutation_executor_result",
            "contract_location": "execution_trace.contracts.mutation_executor_result",
            "blocked_by": "mutation_apply_guard",
        },
        "future_success_surface": {
            "kind": "top_level_apply_success",
            "top_level_ok": True,
            "top_level_error": None,
            "result_location": "result",
            "result_schema_version": REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION,
            "promoted_fields": [
                "reindex_summary",
                "audit_receipt_ref",
                "rollback_hint",
            ],
            "retained_contracts": [
                "mutation_executor",
                "mutation_executor_result",
                "mutation_success_promotion",
            ],
        },
        "promotion_gate": {
            "default_behavior": "remain_blocked_success_sidecar",
            "actual_side_effect_enabled": False,
            "requires": [
                "mutation_apply_guard_execution_enabled",
                "executor_result_ok",
                "live_result_skeleton",
                "durable_audit_ready",
                "explicit_live_adapter_binding",
            ],
        },
        "result_summary": {
            "collection_key": reindex_summary.get("collection_key"),
            "operation": reindex_summary.get("operation"),
            "requested_reset": reindex_summary.get("requested_reset"),
            "requested_compatibility_bundle": reindex_summary.get("requested_compatibility_bundle"),
            "audit_sequence_id": audit_receipt_ref.get("sequence_id"),
            "rollback_mode": rollback_hint.get("mode"),
        },
    }


def build_reindex_live_failure_contract(
    code: str,
    *,
    details: dict[str, object] | None = None,
) -> dict[str, object] | None:
    taxonomy = REINDEX_LIVE_ADAPTER_FAILURE_TAXONOMY.get(str(code or "").strip())
    if taxonomy is None:
        return None
    normalized_details = dict(details) if isinstance(details, dict) else {}
    return {
        "schema_version": REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
        "tool_name": REINDEX_FIRST_LIVE_SCOPE,
        "code": str(code).strip(),
        "stage": str(taxonomy["stage"]),
        "retryable": bool(taxonomy["retryable"]),
        "trigger": str(taxonomy["trigger"]),
        "message": str(taxonomy["message"]),
        "current_surface": {
            "kind": "draft_only_not_runtime_reachable",
            "top_level_ok": False,
            "top_level_error_code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
            "blocked_by": "mutation_apply_guard",
        },
        "future_failure_surface": {
            "kind": "top_level_apply_failure",
            "top_level_ok": False,
            "error_location": "error",
            "error_schema_version": REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
            "retained_contracts": [
                "mutation_executor",
                "mutation_failure_taxonomy",
            ],
        },
        "default_behavior": "not_emitted_until_actual_live_adapter_execution",
        "details": normalized_details,
    }


def list_reindex_live_failure_contracts() -> tuple[dict[str, object], ...]:
    contracts = [
        build_reindex_live_failure_contract(code)
        for code in REINDEX_LIVE_ADAPTER_FAILURE_ORDER
    ]
    return tuple(contract for contract in contracts if contract is not None)


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


@dataclass(frozen=True)
class ReindexLiveMutationExecutorBindingStub:
    executor_name: str = REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    binding_kind: str = REINDEX_LIVE_ADAPTER_BINDING_KIND
    selection_state: str = "live_binding_stub"
    selection_reason: str = "explicit_live_binding_requested"
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
                registered_executor_name=REINDEX_MUTATION_EXECUTOR_NAME,
                delegate_executor_name=NOOP_MUTATION_EXECUTOR_NAME,
            ),
        }


@dataclass(frozen=True)
class ReindexLiveMutationExecutorSkeleton:
    executor_name: str = REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    binding_kind: str = REINDEX_LIVE_ADAPTER_BINDING_KIND
    selection_state: str = "live_result_skeleton"
    selection_reason: str = "explicit_live_result_contract_requested"
    activation_contract: dict[str, object] | None = None
    boundary_contract: dict[str, object] | None = None

    def supports(self, tool_name: str) -> bool:
        return tool_name == "reindex"

    def execute(self, request: MutationExecutionRequest) -> dict[str, object]:
        activation_contract = dict(self.activation_contract) if isinstance(self.activation_contract, dict) else _build_activation_contract(request)
        boundary_contract = dict(self.boundary_contract) if isinstance(self.boundary_contract, dict) else _build_boundary_contract(request)
        return {
            "ok": True,
            "result": _build_reindex_live_result(request),
            "error": None,
            "executor": _build_executor_contract(
                request=request,
                executor_name=self.executor_name,
                binding_kind=self.binding_kind,
                tool_registered=True,
                execution_enabled=True,
                activation_contract=activation_contract,
                boundary_contract=boundary_contract,
                selection_state=self.selection_state,
                selection_reason=self.selection_reason,
                registered_executor_name=REINDEX_MUTATION_EXECUTOR_NAME,
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
    live_binding = _resolve_reindex_live_binding(request)
    if isinstance(live_binding, dict):
        if live_binding.get("binding_stage") == REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON:
            return ReindexLiveMutationExecutorSkeleton(
                activation_contract=activation_contract,
                boundary_contract=boundary_contract,
            )
        return ReindexLiveMutationExecutorBindingStub(
            activation_contract=activation_contract,
            boundary_contract=boundary_contract,
        )
    return ReindexMutationExecutorAdapter(
        activation_contract=activation_contract,
        boundary_contract=boundary_contract,
    )


def execute_mutation_request(request: MutationExecutionRequest) -> dict[str, object]:
    executor = resolve_mutation_executor(request)
    return executor.execute(request)
