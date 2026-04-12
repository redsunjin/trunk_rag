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


def _error_code(result: dict[str, object]) -> str | None:
    error = result.get("error")
    if not isinstance(error, dict):
        return None
    code = error.get("code")
    return str(code) if code is not None else None


def _summarize_result(result: dict[str, object]) -> dict[str, object]:
    trace = result.get("execution_trace") if isinstance(result.get("execution_trace"), dict) else {}
    return {
        "ok": result.get("ok") is True,
        "error_code": _error_code(result),
        "request_id": trace.get("request_id"),
        "selected_tool": result.get("entry", {}).get("selected_tool") if isinstance(result.get("entry"), dict) else None,
        "blocked_by": trace.get("middleware", {}).get("blocked_by") if isinstance(trace.get("middleware"), dict) else None,
    }


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
        "ok": all(check["ok"] for check in checks),
        "checks": checks,
    }


def main() -> int:
    result = run_smoke()
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result["ok"] is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
