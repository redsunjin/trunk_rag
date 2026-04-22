from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common import load_project_env
from services import agent_runtime_service, mutation_executor_service

MUTATION_ACTIVATION_SMOKE_SCHEMA_VERSION = "v1.5.mutation_activation_smoke.v1"
MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_ENV_KEY = "DOC_RAG_MUTATION_SMOKE_LIVE_BINDING"
MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_STAGE_ENV_KEY = "DOC_RAG_MUTATION_SMOKE_LIVE_BINDING_STAGE"
MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE = "smoke_harness"


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _error_code(result: dict[str, object]) -> str | None:
    error = _safe_dict(result.get("error"))
    code = error.get("code")
    return str(code) if code is not None else None


def _summarize_apply_envelope(result: dict[str, object]) -> dict[str, object] | None:
    error = _safe_dict(result.get("error"))
    execution_trace = _safe_dict(result.get("execution_trace"))
    contracts = _safe_dict(execution_trace.get("contracts"))
    envelope = _safe_dict(error.get("apply_envelope")) or _safe_dict(contracts.get("apply_envelope"))
    if not envelope:
        return None
    preview_ref = _safe_dict(envelope.get("preview_ref"))
    audit_ref = _safe_dict(envelope.get("audit_ref"))
    apply_control = _safe_dict(envelope.get("apply_control"))
    return {
        "schema_version": envelope.get("schema_version"),
        "preview_tool_name": preview_ref.get("tool_name"),
        "preview_target": preview_ref.get("target"),
        "audit_sink_type": audit_ref.get("sink_type"),
        "audit_sequence_id": audit_ref.get("sequence_id"),
        "execution_enabled": apply_control.get("execution_enabled"),
    }


def _summarize_audit_sink(result: dict[str, object]) -> dict[str, object] | None:
    execution_trace = _safe_dict(result.get("execution_trace"))
    contracts = _safe_dict(execution_trace.get("contracts"))
    audit_sink = _safe_dict(contracts.get("audit_sink"))
    if not audit_sink:
        return None
    return {
        "sink_type": audit_sink.get("sink_type"),
        "sequence_id": audit_sink.get("sequence_id"),
        "storage_path": audit_sink.get("storage_path"),
        "retention_days": audit_sink.get("retention_days"),
        "prune_policy": audit_sink.get("prune_policy"),
    }


def _summarize_mutation_executor(result: dict[str, object]) -> dict[str, object] | None:
    error = _safe_dict(result.get("error"))
    execution_trace = _safe_dict(result.get("execution_trace"))
    contracts = _safe_dict(execution_trace.get("contracts"))
    executor = _safe_dict(error.get("mutation_executor")) or _safe_dict(contracts.get("mutation_executor"))
    if not executor:
        return None
    activation = _safe_dict(executor.get("activation"))
    boundary = _safe_dict(executor.get("boundary"))
    summary = {
        "executor_name": executor.get("executor_name"),
        "selection_state": executor.get("selection_state"),
        "selection_reason": executor.get("selection_reason"),
        "activation_requested": executor.get("activation_requested"),
        "execution_enabled": executor.get("execution_enabled"),
        "activation_blocked_by": activation.get("blocked_by"),
        "audit_sink_type": activation.get("audit_sink_type"),
        "audit_sequence_id": activation.get("audit_sequence_id"),
        "boundary_family": boundary.get("family"),
        "boundary_classification": boundary.get("classification"),
    }
    if "actual_runtime_handler" in executor:
        summary["actual_runtime_handler"] = executor.get("actual_runtime_handler")
    if "actual_runtime_handler_invoked" in executor:
        summary["actual_runtime_handler_invoked"] = executor.get("actual_runtime_handler_invoked")
    return summary


def _summarize_mutation_executor_result(result: dict[str, object]) -> dict[str, object] | None:
    error = _safe_dict(result.get("error"))
    execution_trace = _safe_dict(result.get("execution_trace"))
    contracts = _safe_dict(execution_trace.get("contracts"))
    executor_result = _safe_dict(error.get("mutation_executor_result")) or _safe_dict(contracts.get("mutation_executor_result"))
    if not executor_result:
        return None
    reindex_summary = _safe_dict(executor_result.get("reindex_summary"))
    audit_receipt_ref = _safe_dict(executor_result.get("audit_receipt_ref"))
    rollback_hint = _safe_dict(executor_result.get("rollback_hint"))
    runtime_result = _safe_dict(executor_result.get("runtime_result"))
    summary = {
        "schema_version": executor_result.get("schema_version"),
        "collection_key": reindex_summary.get("collection_key"),
        "operation": reindex_summary.get("operation"),
        "requested_reset": reindex_summary.get("requested_reset"),
        "requested_compatibility_bundle": reindex_summary.get("requested_compatibility_bundle"),
        "audit_sequence_id": audit_receipt_ref.get("sequence_id"),
        "audit_storage_path": audit_receipt_ref.get("storage_path"),
        "rollback_mode": rollback_hint.get("mode"),
        "rollback_collection_key": rollback_hint.get("collection_key"),
    }
    if "runtime_chunks" in reindex_summary:
        summary["runtime_chunks"] = reindex_summary.get("runtime_chunks")
    if "runtime_vectors" in reindex_summary:
        summary["runtime_vectors"] = reindex_summary.get("runtime_vectors")
    if "runtime_scope" in reindex_summary:
        summary["runtime_scope"] = reindex_summary.get("runtime_scope")
    if runtime_result:
        summary["runtime_collection"] = runtime_result.get("collection")
        summary["runtime_reindex_scope"] = runtime_result.get("reindex_scope")
    return summary


def _summarize_mutation_success_promotion(result: dict[str, object]) -> dict[str, object] | None:
    error = _safe_dict(result.get("error"))
    execution_trace = _safe_dict(result.get("execution_trace"))
    contracts = _safe_dict(execution_trace.get("contracts"))
    promotion = _safe_dict(error.get("mutation_success_promotion")) or _safe_dict(
        contracts.get("mutation_success_promotion")
    )
    if not promotion:
        return None
    current_surface = _safe_dict(promotion.get("current_surface"))
    future_surface = _safe_dict(promotion.get("future_success_surface"))
    promotion_gate = _safe_dict(promotion.get("promotion_gate"))
    return {
        "schema_version": promotion.get("schema_version"),
        "promotion_state": promotion.get("promotion_state"),
        "current_kind": current_surface.get("kind"),
        "current_result_location": current_surface.get("result_location"),
        "future_kind": future_surface.get("kind"),
        "future_result_location": future_surface.get("result_location"),
        "future_top_level_ok": future_surface.get("top_level_ok"),
        "actual_side_effect_enabled": promotion_gate.get("actual_side_effect_enabled"),
    }


def _summarize_mutation_top_level_promotion_router(result: dict[str, object]) -> dict[str, object] | None:
    error = _safe_dict(result.get("error"))
    execution_trace = _safe_dict(result.get("execution_trace"))
    contracts = _safe_dict(execution_trace.get("contracts"))
    router = _safe_dict(error.get("mutation_top_level_promotion_router")) or _safe_dict(
        contracts.get("mutation_top_level_promotion_router")
    )
    if not router:
        return None
    success_route = _safe_dict(router.get("success_route"))
    failure_route = _safe_dict(router.get("failure_route"))
    promotion_gate = _safe_dict(router.get("promotion_gate"))
    supported_codes = failure_route.get("supported_codes")
    return {
        "schema_version": router.get("schema_version"),
        "router_state": router.get("router_state"),
        "success_eligible": success_route.get("eligible"),
        "success_target_result_location": success_route.get("target_result_location"),
        "success_target_top_level_ok": success_route.get("target_top_level_ok"),
        "failure_target_error_location": failure_route.get("target_error_location"),
        "failure_code_count": len(supported_codes) if isinstance(supported_codes, list) else 0,
        "top_level_promotion_enabled": promotion_gate.get("top_level_promotion_enabled"),
        "actual_side_effect_enabled": promotion_gate.get("actual_side_effect_enabled"),
    }


def _summarize_result(result: dict[str, object]) -> dict[str, object]:
    trace = _safe_dict(result.get("execution_trace"))
    summary = {
        "ok": result.get("ok") is True,
        "error_code": _error_code(result),
        "request_id": trace.get("request_id"),
        "selected_tool": _safe_dict(result.get("entry")).get("selected_tool"),
        "blocked_by": _safe_dict(trace.get("middleware")).get("blocked_by"),
    }
    apply_envelope = _summarize_apply_envelope(result)
    if apply_envelope is not None:
        summary["apply_envelope"] = apply_envelope
    audit_sink = _summarize_audit_sink(result)
    if audit_sink is not None:
        summary["audit_sink"] = audit_sink
    mutation_executor = _summarize_mutation_executor(result)
    if mutation_executor is not None:
        summary["mutation_executor"] = mutation_executor
    mutation_executor_result = _summarize_mutation_executor_result(result)
    if mutation_executor_result is not None:
        summary["mutation_executor_result"] = mutation_executor_result
    mutation_success_promotion = _summarize_mutation_success_promotion(result)
    if mutation_success_promotion is not None:
        summary["mutation_success_promotion"] = mutation_success_promotion
    mutation_top_level_promotion_router = _summarize_mutation_top_level_promotion_router(result)
    if mutation_top_level_promotion_router is not None:
        summary["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
    return summary


def _parse_bool_env(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _resolve_live_binding_stage(
    opt_in_live_binding_stage_concrete: bool,
    opt_in_live_binding_stage_guarded: bool,
) -> str | None:
    if opt_in_live_binding_stage_concrete and opt_in_live_binding_stage_guarded:
        raise ValueError("choose only one live binding stage flag")
    if opt_in_live_binding_stage_guarded:
        return mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_GUARDED_LIVE_EXECUTOR
    if opt_in_live_binding_stage_concrete:
        return mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON
    raw_stage = os.getenv(MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_STAGE_ENV_KEY)
    normalized_stage = raw_stage.strip() if isinstance(raw_stage, str) else ""
    return normalized_stage or None


def _build_live_binding(opt_in_live_binding: bool, live_binding_stage: str | None) -> dict[str, object] | None:
    if not opt_in_live_binding:
        return None
    binding = {
        "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
        "binding_source": MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE,
        "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
    }
    if live_binding_stage:
        binding[mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD] = live_binding_stage
    return binding


def run_smoke(
    *,
    opt_in_live_binding: bool | None = None,
    opt_in_live_binding_stage_concrete: bool = False,
    opt_in_live_binding_stage_guarded: bool = False,
) -> dict[str, object]:
    load_project_env()
    resolved_opt_in_live_binding = (
        _parse_bool_env(os.getenv(MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_ENV_KEY))
        if opt_in_live_binding is None
        else bool(opt_in_live_binding)
    )
    resolved_live_binding_stage = _resolve_live_binding_stage(
        opt_in_live_binding_stage_concrete,
        opt_in_live_binding_stage_guarded,
    )
    executor_binding = _build_live_binding(resolved_opt_in_live_binding, resolved_live_binding_stage)
    reindex_apply_payload: dict[str, object] = {"collection": "all"}
    if (
        resolved_live_binding_stage
        == mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON
    ):
        reindex_apply_payload["include_compatibility_bundle"] = True
    read_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Check internal runtime health.",
            tool_name="health_check",
            request_id="agent-smoke-read",
            timeout_seconds=5,
        )
    )
    read_only_write_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Try a write tool without mutation permission.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            request_id="agent-smoke-write-read-only",
            timeout_seconds=5,
        )
    )
    auth_required_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Run maintenance reindex.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            request_id="agent-smoke-auth",
            allow_mutation=True,
            timeout_seconds=5,
        )
    )
    intent_required_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Run maintenance reindex.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            request_id="agent-smoke-intent",
            allow_mutation=True,
            timeout_seconds=5,
        )
    )
    preview_required_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Run maintenance reindex.",
            tool_name="reindex",
            tool_payload=dict(reindex_apply_payload),
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex core all collection",
            request_id="agent-smoke-preview",
            allow_mutation=True,
            timeout_seconds=5,
        )
    )
    preview_error = preview_required_result.get("error") if isinstance(preview_required_result.get("error"), dict) else {}
    apply_envelope = preview_error.get("apply_envelope") if isinstance(preview_error.get("apply_envelope"), dict) else None
    apply_not_enabled_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed maintenance reindex.",
            tool_name="reindex",
            tool_payload=dict(reindex_apply_payload),
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex core all collection",
            apply_envelope=apply_envelope,
            executor_binding=executor_binding,
            request_id="agent-smoke-apply",
            allow_mutation=True,
            timeout_seconds=5,
        )
    )
    checks = [
        {
            "name": "read_only_health_check",
            "ok": read_result.get("ok") is True,
            "summary": _summarize_result(read_result),
        },
        {
            "name": "write_tool_blocked_read_only",
            "ok": read_only_write_result.get("ok") is False and _error_code(read_only_write_result) == "TOOL_NOT_ALLOWED",
            "summary": _summarize_result(read_only_write_result),
        },
        {
            "name": "write_tool_requires_admin_auth",
            "ok": auth_required_result.get("ok") is False and _error_code(auth_required_result) == "ADMIN_AUTH_REQUIRED",
            "summary": _summarize_result(auth_required_result),
        },
        {
            "name": "write_tool_requires_mutation_intent",
            "ok": intent_required_result.get("ok") is False and _error_code(intent_required_result) == "MUTATION_INTENT_REQUIRED",
            "summary": _summarize_result(intent_required_result),
        },
        {
            "name": "write_tool_requires_preview",
            "ok": preview_required_result.get("ok") is False and _error_code(preview_required_result) == "PREVIEW_REQUIRED",
            "summary": _summarize_result(preview_required_result),
        },
        {
            "name": "write_tool_apply_not_enabled",
            "ok": apply_not_enabled_result.get("ok") is False and _error_code(apply_not_enabled_result) == "MUTATION_APPLY_NOT_ENABLED",
            "summary": _summarize_result(apply_not_enabled_result),
        },
    ]
    return {
        "schema_version": MUTATION_ACTIVATION_SMOKE_SCHEMA_VERSION,
        "requested_live_binding": resolved_opt_in_live_binding,
        "requested_live_binding_stage": resolved_live_binding_stage,
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }


def main() -> int:
    args = sys.argv[1:]
    opt_in_live_binding = True if "--opt-in-live-binding" in args else None
    opt_in_live_binding_stage_concrete = "--opt-in-live-binding-stage-concrete" in sys.argv[1:]
    opt_in_live_binding_stage_guarded = "--opt-in-live-binding-stage-guarded" in sys.argv[1:]
    try:
        result = run_smoke(
            opt_in_live_binding=opt_in_live_binding,
            opt_in_live_binding_stage_concrete=opt_in_live_binding_stage_concrete,
            opt_in_live_binding_stage_guarded=opt_in_live_binding_stage_guarded,
        )
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
