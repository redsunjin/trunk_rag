from __future__ import annotations

from dataclasses import dataclass

from services import tool_middleware_service
from services.tool_registry_service import ToolContext, ToolPayload

DEFAULT_AGENT_TOOL_ALLOWLIST = (
    "search_docs",
    "read_doc",
    "list_collections",
    "health_check",
    "list_upload_requests",
)


@dataclass(frozen=True)
class AgentRuntimeRequest:
    input: str
    tool_name: str = "search_docs"
    tool_payload: ToolPayload | None = None
    request_id: str = "-"
    actor: str = "internal_agent"
    allow_mutation: bool = False
    allowed_tools: tuple[str, ...] | None = None
    timeout_seconds: float | None = None


def _error_response(code: str, message: str, *, request_id: str = "-") -> dict[str, object]:
    return {
        "ok": False,
        "entry": {
            "mode": "single_tool_draft",
            "request_id": request_id,
        },
        "tool_call": None,
        "execution_trace": None,
        "error": {
            "code": code,
            "message": message,
        },
    }


def _normalize_tool_name(tool_name: str) -> str:
    return (tool_name or "search_docs").strip() or "search_docs"


def _build_default_payload(tool_name: str, user_input: str) -> ToolPayload:
    if tool_name == "search_docs":
        return {"query": user_input}
    if tool_name in {"list_collections", "health_check", "list_upload_requests"}:
        return {}
    return {"input": user_input}


def run_agent_entry(request: AgentRuntimeRequest) -> dict[str, object]:
    user_input = str(request.input or "").strip()
    if not user_input:
        return _error_response(
            "INVALID_AGENT_INPUT",
            "Agent runtime entry requires a non-empty input.",
            request_id=request.request_id,
        )

    tool_name = _normalize_tool_name(request.tool_name)
    payload = dict(request.tool_payload) if isinstance(request.tool_payload, dict) else _build_default_payload(tool_name, user_input)
    allowed_tools = request.allowed_tools if request.allowed_tools is not None else DEFAULT_AGENT_TOOL_ALLOWLIST
    context = ToolContext(
        request_id=request.request_id,
        actor=request.actor,
        allow_mutation=request.allow_mutation,
        timeout_seconds=request.timeout_seconds,
    )
    tool_call = tool_middleware_service.invoke_tool_with_middlewares(
        tool_name,
        payload,
        context=context,
        allowed_tools=allowed_tools,
        timeout_seconds=request.timeout_seconds,
    )
    execution_trace = tool_call.get("execution_trace") if isinstance(tool_call.get("execution_trace"), dict) else None
    trace_request_id = execution_trace.get("request_id", request.request_id) if execution_trace else request.request_id
    return {
        "ok": tool_call.get("ok") is True,
        "entry": {
            "mode": "single_tool_draft",
            "request_id": trace_request_id,
            "input": user_input,
            "selected_tool": tool_name,
            "allowed_tools": list(allowed_tools),
        },
        "tool_call": tool_call,
        "execution_trace": execution_trace,
        "error": tool_call.get("error"),
    }
