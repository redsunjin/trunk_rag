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
    write_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Try a write tool without mutation permission.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            request_id="agent-smoke-write",
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
            "name": "write_tool_blocked",
            "ok": write_result.get("ok") is False and _error_code(write_result) == "TOOL_NOT_ALLOWED",
            "summary": _summarize_result(write_result),
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
