from __future__ import annotations

from dataclasses import dataclass

from services import actor_policy_service, tool_middleware_service
from services.tool_registry_service import ToolContext, ToolPayload


@dataclass(frozen=True)
class AgentRuntimeRequest:
    input: str
    tool_name: str = "search_docs"
    tool_payload: ToolPayload | None = None
    request_id: str = "-"
    actor: str = "internal_agent"
    allow_mutation: bool = False
    admin_code: str | None = None
    mutation_intent: str | None = None
    apply_envelope: dict[str, object] | None = None
    executor_binding: dict[str, object] | None = None
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


def _normalize_allowed_tools(allowed_tools: tuple[str, ...] | None) -> tuple[str, ...] | None:
    if allowed_tools is None:
        return None
    normalized = tuple(str(tool_name).strip() for tool_name in allowed_tools if str(tool_name).strip())
    return normalized or None


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_optional_object(value: object) -> dict[str, object] | None:
    if not isinstance(value, dict):
        return None
    return dict(value)


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
    policy_decision = actor_policy_service.resolve_actor_policy(request.actor)
    requested_allowed_tools = _normalize_allowed_tools(request.allowed_tools)
    allowed_tools = actor_policy_service.resolve_allowed_tools(
        policy_decision,
        tool_name=tool_name,
        requested_allowed_tools=requested_allowed_tools,
    )
    admin_code = _normalize_optional_text(request.admin_code) or _normalize_optional_text(payload.get("admin_code")) or _normalize_optional_text(payload.get("code"))
    mutation_intent = _normalize_optional_text(request.mutation_intent) or _normalize_optional_text(payload.get("mutation_intent"))
    apply_envelope = _normalize_optional_object(request.apply_envelope) or _normalize_optional_object(payload.get("apply_envelope"))
    executor_binding = _normalize_optional_object(request.executor_binding)
    context = ToolContext(
        request_id=request.request_id,
        actor=request.actor,
        allow_mutation=request.allow_mutation,
        timeout_seconds=request.timeout_seconds,
        admin_code=admin_code,
        mutation_intent=mutation_intent,
        apply_envelope=apply_envelope,
        executor_binding=executor_binding,
    )
    tool_call = tool_middleware_service.invoke_tool_with_middlewares(
        tool_name,
        payload,
        context=context,
        allowed_tools=allowed_tools,
        policy_decision=policy_decision,
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
            "actor_category": policy_decision.actor_category,
            "allowed_tools": list(allowed_tools),
            "mutation_candidate_tools": list(policy_decision.mutation_candidate_tools),
            "admin_code_present": admin_code is not None,
            "mutation_intent_present": mutation_intent is not None,
            "apply_envelope_present": apply_envelope is not None,
            "executor_binding_present": executor_binding is not None,
            "policy_flags": {
                "requires_admin_auth": policy_decision.requires_admin_auth,
                "requires_mutation_intent": policy_decision.requires_mutation_intent,
                "requires_preview_before_apply": policy_decision.requires_preview_before_apply,
                "audit_scope": policy_decision.audit_scope,
                "used_fallback": policy_decision.used_fallback,
            },
        },
        "tool_call": tool_call,
        "execution_trace": execution_trace,
        "error": tool_call.get("error"),
    }
