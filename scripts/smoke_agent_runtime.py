from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from common import load_project_env
from services import agent_runtime_service

MUTATION_ACTIVATION_SMOKE_SCHEMA_VERSION = "v1.5.mutation_activation_smoke.v1"


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
    return {
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
    return summary


def run_smoke() -> dict[str, object]:
    load_project_env()
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
            tool_payload={"collection": "all"},
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
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex core all collection",
            apply_envelope=apply_envelope,
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
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }


def main() -> int:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
