from __future__ import annotations

from dataclasses import dataclass, field, replace
import time
from typing import Callable
from uuid import uuid4

from services import (
    actor_policy_service,
    mutation_executor_service,
    runtime_service,
    tool_apply_service,
    tool_audit_sink_service,
    tool_preview_service,
    tool_registry_service,
    tool_trace_service,
)
from services.tool_registry_service import ToolContext, ToolInputError, ToolPayload

ToolExecutionResult = dict[str, object]
ToolMiddleware = Callable[["ToolExecutionState"], None]


@dataclass
class ToolExecutionState:
    tool_name: str
    payload: ToolPayload
    context: ToolContext
    definition: dict[str, object]
    policy_decision: actor_policy_service.ActorPolicyDecision | None = None
    allowed_tools: tuple[str, ...] | None = None
    timeout_seconds: float | None = None
    started_at: float = field(default_factory=time.monotonic)
    middleware_trace: list[dict[str, object]] = field(default_factory=list)
    audit_log: list[dict[str, object]] = field(default_factory=list)
    blocked_result: ToolExecutionResult | None = None
    preview_contract: dict[str, object] | None = None
    preview_seed: dict[str, object] | None = None
    apply_envelope: dict[str, object] | None = None
    persisted_audit_record: dict[str, object] | None = None
    audit_sink_receipt: dict[str, object] | None = None
    mutation_executor_contract: dict[str, object] | None = None
    mutation_executor_result: dict[str, object] | None = None
    mutation_executor_error: dict[str, object] | None = None
    mutation_success_promotion: dict[str, object] | None = None
    mutation_top_level_promotion_router: dict[str, object] | None = None
    mutation_apply_router_dry_run: dict[str, object] | None = None

    @property
    def side_effect(self) -> str:
        return str(self.definition.get("side_effect", "")).strip().lower()

    @property
    def elapsed_ms(self) -> int:
        return int((time.monotonic() - self.started_at) * 1000)


def _normalize_payload(payload: ToolPayload | None) -> ToolPayload:
    resolved_payload = payload or {}
    if not isinstance(resolved_payload, dict):
        raise ToolInputError("payload must be an object.")
    return resolved_payload


def _normalize_allowed_tools(allowed_tools: list[str] | tuple[str, ...] | None) -> tuple[str, ...] | None:
    if allowed_tools is None:
        return None
    return tuple(str(name).strip() for name in allowed_tools if str(name).strip())


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _resolve_request_id(request_id: str) -> str:
    normalized = request_id.strip()
    if normalized and normalized != "-":
        return normalized
    return f"tool-{uuid4().hex[:12]}"


def _append_trace(
    state: ToolExecutionState,
    middleware: str,
    status: str,
    *,
    detail: dict[str, object] | None = None,
) -> None:
    item: dict[str, object] = {
        "middleware": middleware,
        "status": status,
        "elapsed_ms": state.elapsed_ms,
    }
    if detail:
        item["detail"] = detail
    state.middleware_trace.append(item)


def _append_audit(state: ToolExecutionState, event: str, **fields: object) -> None:
    state.audit_log.append(
        {
            "event": event,
            "request_id": state.context.request_id,
            "tool": state.tool_name,
            "actor": state.context.actor,
            "elapsed_ms": state.elapsed_ms,
            **fields,
        }
    )


def _error_result(tool_name: str, code: str, message: str, **fields: object) -> ToolExecutionResult:
    return {
        "tool": tool_name,
        "ok": False,
        "result": None,
        "error": {
            "code": code,
            "message": message,
            **fields,
        },
    }


def _attach_middleware_metadata(
    result: ToolExecutionResult,
    state: ToolExecutionState,
) -> ToolExecutionResult:
    enriched = dict(result)
    allowed_tools = list(state.allowed_tools) if state.allowed_tools is not None else None
    policy_details = state.policy_decision.as_dict() if state.policy_decision else None
    preview_contract = state.preview_contract
    if preview_contract is None:
        preview_contract = tool_trace_service.build_preview_contract(
            request_id=state.context.request_id,
            tool_name=state.tool_name,
            side_effect=state.side_effect,
            payload=state.payload,
            policy_details=policy_details,
        )
    preview_seed = state.preview_seed
    if preview_seed is None and preview_contract is not None:
        preview_seed = tool_preview_service.build_preview_seed(
            preview_contract,
            payload=state.payload,
        )
    middleware_metadata = {
        "request_id": state.context.request_id,
        "actor": state.context.actor,
        "allow_mutation": state.context.allow_mutation,
        "timeout_seconds": state.timeout_seconds,
        "allowed_tools": allowed_tools,
        "policy": policy_details,
        "elapsed_ms": state.elapsed_ms,
        "trace": list(state.middleware_trace),
        "audit_log": list(state.audit_log),
    }
    execution_trace = tool_trace_service.build_execution_trace(
        request_id=state.context.request_id,
        actor=state.context.actor,
        tool_name=state.tool_name,
        side_effect=state.side_effect,
        allow_mutation=state.context.allow_mutation,
        allowed_tools=allowed_tools,
        policy_details=policy_details,
        timeout_seconds=state.timeout_seconds,
        elapsed_ms=state.elapsed_ms,
        middleware_steps=list(state.middleware_trace),
        audit_events=list(state.audit_log),
        result=result,
    )
    persisted_audit_record = state.persisted_audit_record or tool_trace_service.build_persisted_audit_record(execution_trace)
    audit_sink_receipt = state.audit_sink_receipt or tool_audit_sink_service.append_persisted_audit_record(
        persisted_audit_record
    )
    mutation_executor_contract = state.mutation_executor_contract
    mutation_executor_result = state.mutation_executor_result
    mutation_executor_error = state.mutation_executor_error
    mutation_success_promotion = state.mutation_success_promotion
    mutation_top_level_promotion_router = state.mutation_top_level_promotion_router
    mutation_apply_router_dry_run = state.mutation_apply_router_dry_run
    if isinstance(enriched.get("error"), dict):
        error = dict(enriched["error"])
        if error.get("code") == tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED:
            if mutation_executor_contract is None:
                mutation_request = _build_mutation_execution_request(
                    state,
                    persisted_audit_record=persisted_audit_record,
                    audit_sink_receipt=audit_sink_receipt,
                )
                if mutation_request is not None:
                    executor_result = mutation_executor_service.execute_mutation_request(mutation_request)
                    executor_error = executor_result.get("error")
                    if isinstance(executor_error, dict):
                        mutation_executor_error = dict(executor_error)
                    executor_contract = executor_result.get("executor")
                    if isinstance(executor_contract, dict):
                        mutation_executor_contract = dict(executor_contract)
                    executor_payload = executor_result.get("result")
                    if isinstance(executor_payload, dict):
                        mutation_executor_result = dict(executor_payload)
            if mutation_success_promotion is None:
                mutation_success_promotion = mutation_executor_service.build_reindex_live_success_promotion_contract(
                    executor_contract=mutation_executor_contract,
                    executor_result=mutation_executor_result,
                )
            if mutation_top_level_promotion_router is None:
                mutation_top_level_promotion_router = (
                    mutation_executor_service.build_reindex_top_level_promotion_router_contract(
                        executor_contract=mutation_executor_contract,
                        executor_result=mutation_executor_result,
                        executor_error=mutation_executor_error,
                        mutation_success_promotion=mutation_success_promotion,
                    )
                )
            if mutation_apply_router_dry_run is None:
                mutation_apply_router_dry_run = (
                    mutation_executor_service.build_reindex_mutation_apply_router_dry_run_contract(
                        executor_contract=mutation_executor_contract,
                        executor_result=mutation_executor_result,
                        mutation_success_promotion=mutation_success_promotion,
                    )
                )
            if mutation_executor_contract is not None:
                error["mutation_executor"] = mutation_executor_contract
            if mutation_executor_result is not None:
                error["mutation_executor_result"] = mutation_executor_result
            if mutation_executor_error is not None:
                error["mutation_executor_error"] = mutation_executor_error
            if mutation_success_promotion is not None:
                error["mutation_success_promotion"] = mutation_success_promotion
            if mutation_top_level_promotion_router is not None:
                error["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
            if mutation_apply_router_dry_run is not None:
                error["mutation_apply_router_dry_run"] = mutation_apply_router_dry_run
            enriched["error"] = error
    mutation_intent_summary = _resolve_mutation_intent(state)
    apply_envelope_draft = tool_apply_service.build_mutation_apply_envelope(
        preview_seed=preview_seed,
        audit_sink_receipt=audit_sink_receipt,
        mutation_intent_summary=mutation_intent_summary,
    )
    contracts: dict[str, object] = {
        "persisted_audit": persisted_audit_record,
        "audit_sink": audit_sink_receipt,
    }
    if preview_contract is not None:
        contracts["preview"] = preview_contract
    if preview_seed is not None:
        contracts["preview_seed"] = preview_seed
    if apply_envelope_draft is not None:
        contracts["apply_envelope"] = apply_envelope_draft
    if mutation_executor_contract is not None:
        contracts["mutation_executor"] = mutation_executor_contract
    if mutation_executor_result is not None:
        contracts["mutation_executor_result"] = mutation_executor_result
    if mutation_executor_error is not None:
        contracts["mutation_executor_error"] = mutation_executor_error
    if mutation_success_promotion is not None:
        contracts["mutation_success_promotion"] = mutation_success_promotion
    if mutation_top_level_promotion_router is not None:
        contracts["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
    if mutation_apply_router_dry_run is not None:
        contracts["mutation_apply_router_dry_run"] = mutation_apply_router_dry_run
    middleware_metadata["contracts"] = contracts
    execution_trace["contracts"] = contracts
    if isinstance(enriched.get("error"), dict):
        updated_error = dict(enriched["error"])
        if apply_envelope_draft is not None:
            updated_error["apply_envelope"] = apply_envelope_draft
        if mutation_executor_contract is not None:
            updated_error["mutation_executor"] = mutation_executor_contract
        if mutation_executor_result is not None:
            updated_error["mutation_executor_result"] = mutation_executor_result
        if mutation_executor_error is not None:
            updated_error["mutation_executor_error"] = mutation_executor_error
        if mutation_success_promotion is not None:
            updated_error["mutation_success_promotion"] = mutation_success_promotion
        if mutation_top_level_promotion_router is not None:
            updated_error["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
        if mutation_apply_router_dry_run is not None:
            updated_error["mutation_apply_router_dry_run"] = mutation_apply_router_dry_run
        enriched["error"] = updated_error
    enriched["middleware"] = middleware_metadata
    enriched["execution_trace"] = execution_trace
    return enriched


def request_id_middleware(state: ToolExecutionState) -> None:
    request_id = _resolve_request_id(state.context.request_id)
    if request_id != state.context.request_id:
        state.context = replace(state.context, request_id=request_id)
    _append_trace(state, "request_id", "ok", detail={"request_id": state.context.request_id})


def timeout_budget_middleware(state: ToolExecutionState) -> None:
    timeout_seconds = state.timeout_seconds
    if timeout_seconds is None:
        timeout_seconds = state.context.timeout_seconds
    if timeout_seconds is None:
        timeout_seconds = float(runtime_service.get_query_timeout_seconds())

    state.timeout_seconds = float(timeout_seconds)
    if state.timeout_seconds <= 0:
        state.blocked_result = _error_result(
            state.tool_name,
            "TIMEOUT_BUDGET_EXHAUSTED",
            "Tool execution requires a positive timeout budget.",
            timeout_seconds=state.timeout_seconds,
        )
        _append_trace(
            state,
            "timeout_budget",
            "blocked",
            detail={"timeout_seconds": state.timeout_seconds},
        )
        return

    if state.context.timeout_seconds != state.timeout_seconds:
        state.context = replace(state.context, timeout_seconds=state.timeout_seconds)
    _append_trace(
        state,
        "timeout_budget",
        "ok",
        detail={"timeout_seconds": state.timeout_seconds},
    )


def tool_allowlist_middleware(state: ToolExecutionState) -> None:
    if state.allowed_tools is None:
        _append_trace(state, "tool_allowlist", "skipped")
        return
    if state.tool_name in state.allowed_tools:
        _append_trace(
            state,
            "tool_allowlist",
            "ok",
            detail={"allowed_tools": list(state.allowed_tools)},
        )
        return

    state.blocked_result = _error_result(
        state.tool_name,
        "TOOL_NOT_ALLOWED",
        "Tool is not present in the middleware allowlist.",
        allowed_tools=list(state.allowed_tools),
    )
    _append_trace(
        state,
        "tool_allowlist",
        "blocked",
        detail={"allowed_tools": list(state.allowed_tools)},
    )


def _resolve_admin_code(state: ToolExecutionState) -> str | None:
    return (
        _normalize_optional_text(state.context.admin_code)
        or _normalize_optional_text(state.payload.get("admin_code"))
        or _normalize_optional_text(state.payload.get("code"))
    )


def _resolve_mutation_intent(state: ToolExecutionState) -> str | None:
    return (
        _normalize_optional_text(state.context.mutation_intent)
        or _normalize_optional_text(state.payload.get("mutation_intent"))
    )


def _resolve_apply_envelope(state: ToolExecutionState) -> dict[str, object] | None:
    if isinstance(state.context.apply_envelope, dict):
        return dict(state.context.apply_envelope)
    payload_apply_envelope = state.payload.get("apply_envelope")
    if isinstance(payload_apply_envelope, dict):
        return dict(payload_apply_envelope)
    return None


def _resolve_executor_binding(state: ToolExecutionState) -> dict[str, object] | None:
    if isinstance(state.context.executor_binding, dict):
        return dict(state.context.executor_binding)
    return None


def _build_mutation_execution_request(
    state: ToolExecutionState,
    *,
    persisted_audit_record: dict[str, object],
    audit_sink_receipt: dict[str, object],
) -> mutation_executor_service.MutationExecutionRequest | None:
    actor_category = state.policy_decision.actor_category if state.policy_decision else None
    return mutation_executor_service.build_mutation_execution_request(
        request_id=state.context.request_id,
        tool_name=state.tool_name,
        payload=state.payload,
        apply_envelope=state.apply_envelope,
        preview_seed=state.preview_seed,
        persisted_audit_record=persisted_audit_record,
        audit_sink_receipt=audit_sink_receipt,
        actor=state.context.actor,
        actor_category=actor_category,
        allow_mutation=state.context.allow_mutation,
        timeout_seconds=state.timeout_seconds,
        executor_binding=_resolve_executor_binding(state),
    )


def _route_pre_side_effect_mutation_executor_dry_run(state: ToolExecutionState) -> None:
    blocked_result = state.blocked_result
    if not isinstance(blocked_result, dict):
        return
    error = blocked_result.get("error")
    if not isinstance(error, dict) or error.get("code") != tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED:
        return
    if state.mutation_executor_contract is not None:
        return

    allowed_tools = list(state.allowed_tools) if state.allowed_tools is not None else None
    policy_details = state.policy_decision.as_dict() if state.policy_decision else None
    execution_trace = tool_trace_service.build_execution_trace(
        request_id=state.context.request_id,
        actor=state.context.actor,
        tool_name=state.tool_name,
        side_effect=state.side_effect,
        allow_mutation=state.context.allow_mutation,
        allowed_tools=allowed_tools,
        policy_details=policy_details,
        timeout_seconds=state.timeout_seconds,
        elapsed_ms=state.elapsed_ms,
        middleware_steps=list(state.middleware_trace),
        audit_events=list(state.audit_log),
        result=blocked_result,
    )
    persisted_audit_record = state.persisted_audit_record or tool_trace_service.build_persisted_audit_record(
        execution_trace
    )
    audit_sink_receipt = state.audit_sink_receipt or tool_audit_sink_service.append_persisted_audit_record(
        persisted_audit_record
    )
    state.persisted_audit_record = persisted_audit_record
    state.audit_sink_receipt = audit_sink_receipt

    mutation_request = _build_mutation_execution_request(
        state,
        persisted_audit_record=persisted_audit_record,
        audit_sink_receipt=audit_sink_receipt,
    )
    if mutation_request is None:
        return

    executor_result = mutation_executor_service.execute_mutation_request(mutation_request)
    executor_contract = executor_result.get("executor")
    if isinstance(executor_contract, dict):
        state.mutation_executor_contract = dict(executor_contract)
    executor_payload = executor_result.get("result")
    if isinstance(executor_payload, dict):
        state.mutation_executor_result = dict(executor_payload)
    executor_error = executor_result.get("error")
    if isinstance(executor_error, dict):
        state.mutation_executor_error = dict(executor_error)
    state.mutation_success_promotion = mutation_executor_service.build_reindex_live_success_promotion_contract(
        executor_contract=state.mutation_executor_contract,
        executor_result=state.mutation_executor_result,
    )
    state.mutation_top_level_promotion_router = mutation_executor_service.build_reindex_top_level_promotion_router_contract(
        executor_contract=state.mutation_executor_contract,
        executor_result=state.mutation_executor_result,
        executor_error=state.mutation_executor_error,
        mutation_success_promotion=state.mutation_success_promotion,
    )
    state.mutation_apply_router_dry_run = mutation_executor_service.build_reindex_mutation_apply_router_dry_run_contract(
        executor_contract=state.mutation_executor_contract,
        executor_result=state.mutation_executor_result,
        mutation_success_promotion=state.mutation_success_promotion,
        route_location="mutation_apply_guard_pre_side_effect_router",
    )


def mutation_policy_guard_middleware(state: ToolExecutionState) -> None:
    if state.side_effect != "write":
        _append_trace(
            state,
            "mutation_policy_guard",
            "ok",
            detail={"side_effect": state.side_effect or "unknown"},
        )
        return

    decision = state.policy_decision
    mutation_candidates = set(decision.mutation_candidate_tools) if decision else set()
    if state.tool_name not in mutation_candidates:
        _append_trace(
            state,
            "mutation_policy_guard",
            "skipped",
            detail={"actor_category": decision.actor_category if decision else None},
        )
        return

    admin_code = _resolve_admin_code(state)
    mutation_intent = _resolve_mutation_intent(state)
    apply_envelope = _resolve_apply_envelope(state)
    detail = {
        "actor_category": decision.actor_category if decision else None,
        "requires_admin_auth": decision.requires_admin_auth if decision else False,
        "requires_mutation_intent": decision.requires_mutation_intent if decision else False,
        "requires_preview_before_apply": decision.requires_preview_before_apply if decision else False,
        "admin_authenticated": False,
        "mutation_intent_present": mutation_intent is not None,
        "apply_envelope_present": apply_envelope is not None,
    }

    if decision and decision.requires_admin_auth:
        if admin_code is None:
            state.blocked_result = _error_result(
                state.tool_name,
                "ADMIN_AUTH_REQUIRED",
                "Mutation candidate tool requires admin authentication.",
            )
            _append_trace(state, "mutation_policy_guard", "blocked", detail=detail)
            return
        try:
            runtime_service.verify_admin_code(admin_code)
        except Exception:
            state.blocked_result = _error_result(
                state.tool_name,
                "ADMIN_AUTH_FAILED",
                "Mutation candidate tool failed admin authentication.",
            )
            _append_trace(state, "mutation_policy_guard", "blocked", detail=detail)
            return
        detail["admin_authenticated"] = True

    if decision and decision.requires_mutation_intent and mutation_intent is None:
        state.blocked_result = _error_result(
            state.tool_name,
            "MUTATION_INTENT_REQUIRED",
            "Mutation candidate tool requires an explicit mutation intent.",
        )
        _append_trace(state, "mutation_policy_guard", "blocked", detail=detail)
        return

    if decision and decision.requires_preview_before_apply:
        preview_contract = tool_trace_service.build_preview_contract(
            request_id=state.context.request_id,
            tool_name=state.tool_name,
            side_effect=state.side_effect,
            payload=state.payload,
            policy_details=decision.as_dict(),
        )
        preview_seed = tool_preview_service.build_preview_seed(
            preview_contract,
            payload=state.payload,
        )
        state.preview_contract = preview_contract
        state.preview_seed = preview_seed
        state.apply_envelope = apply_envelope
        if apply_envelope is not None:
            _append_trace(state, "mutation_policy_guard", "ok", detail=detail)
            return
        state.blocked_result = _error_result(
            state.tool_name,
            "PREVIEW_REQUIRED",
            "Mutation candidate tool requires a preview step before apply.",
            preview_contract=preview_contract,
            preview_seed=preview_seed,
        )
        _append_trace(state, "mutation_policy_guard", "blocked", detail=detail)
        return

    _append_trace(state, "mutation_policy_guard", "ok", detail=detail)


def mutation_apply_guard_middleware(state: ToolExecutionState) -> None:
    if state.side_effect != "write":
        _append_trace(
            state,
            "mutation_apply_guard",
            "ok",
            detail={"side_effect": state.side_effect or "unknown"},
        )
        return

    decision = state.policy_decision
    if not decision or not decision.requires_preview_before_apply:
        _append_trace(
            state,
            "mutation_apply_guard",
            "skipped",
            detail={"actor_category": decision.actor_category if decision else None},
        )
        return

    apply_envelope = state.apply_envelope or _resolve_apply_envelope(state)
    if apply_envelope is None:
        _append_trace(
            state,
            "mutation_apply_guard",
            "skipped",
            detail={"actor_category": decision.actor_category},
        )
        return

    preview_contract = state.preview_contract or tool_trace_service.build_preview_contract(
        request_id=state.context.request_id,
        tool_name=state.tool_name,
        side_effect=state.side_effect,
        payload=state.payload,
        policy_details=decision.as_dict(),
    )
    preview_seed = state.preview_seed or tool_preview_service.build_preview_seed(
        preview_contract,
        payload=state.payload,
    )
    state.preview_contract = preview_contract
    state.preview_seed = preview_seed
    state.apply_envelope = apply_envelope

    validation = tool_apply_service.validate_mutation_apply_envelope(
        apply_envelope,
        preview_seed=preview_seed,
    )
    if validation.get("ok") is not True:
        error = validation.get("error") if isinstance(validation.get("error"), dict) else {}
        state.blocked_result = _error_result(
            state.tool_name,
            str(error.get("code", "MUTATION_APPLY_INVALID")),
            str(error.get("message", "Mutation apply envelope is invalid.")),
            submitted_apply_envelope=apply_envelope,
        )
        _append_trace(
            state,
            "mutation_apply_guard",
            "blocked",
            detail={"actor_category": decision.actor_category, "apply_envelope_present": True},
        )
        return

    state.blocked_result = _error_result(
        state.tool_name,
        tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
        "Mutation apply handshake validated, but execution is not enabled yet.",
        submitted_apply_envelope=apply_envelope,
    )
    _append_trace(
        state,
        "mutation_apply_guard",
        "blocked",
        detail={"actor_category": decision.actor_category, "apply_envelope_present": True},
    )


def unsafe_action_guard_middleware(state: ToolExecutionState) -> None:
    if state.side_effect != "write":
        _append_trace(
            state,
            "unsafe_action_guard",
            "ok",
            detail={"side_effect": state.side_effect or "unknown"},
        )
        return
    if state.context.allow_mutation:
        _append_trace(
            state,
            "unsafe_action_guard",
            "ok",
            detail={"side_effect": state.side_effect, "allow_mutation": True},
        )
        return

    state.blocked_result = _error_result(
        state.tool_name,
        "MUTATION_NOT_ALLOWED",
        "This tool requires ToolContext.allow_mutation=True.",
    )
    _append_trace(
        state,
        "unsafe_action_guard",
        "blocked",
        detail={"side_effect": state.side_effect, "allow_mutation": False},
    )


def audit_log_middleware(state: ToolExecutionState) -> None:
    _append_audit(
        state,
        "tool.invoke.requested",
        side_effect=state.side_effect,
        timeout_seconds=state.timeout_seconds,
    )
    _append_trace(state, "audit_log", "ok")


DEFAULT_TOOL_MIDDLEWARES: tuple[ToolMiddleware, ...] = (
    request_id_middleware,
    timeout_budget_middleware,
    tool_allowlist_middleware,
    mutation_policy_guard_middleware,
    mutation_apply_guard_middleware,
    unsafe_action_guard_middleware,
    audit_log_middleware,
)


def invoke_tool_with_middlewares(
    name: str,
    payload: ToolPayload | None = None,
    *,
    context: ToolContext | None = None,
    allowed_tools: list[str] | tuple[str, ...] | None = None,
    policy_decision: actor_policy_service.ActorPolicyDecision | None = None,
    timeout_seconds: float | None = None,
    middlewares: tuple[ToolMiddleware, ...] | list[ToolMiddleware] | None = None,
) -> ToolExecutionResult:
    resolved_payload = _normalize_payload(payload)
    resolved_context = context or ToolContext()
    resolved_policy_decision = policy_decision or actor_policy_service.resolve_actor_policy(resolved_context.actor)
    normalized_allowed_tools = actor_policy_service.resolve_allowed_tools(
        resolved_policy_decision,
        tool_name=name,
        requested_allowed_tools=_normalize_allowed_tools(allowed_tools),
    )
    try:
        definition = tool_registry_service.get_tool_definition(name)
    except ToolInputError as exc:
        state = ToolExecutionState(
            tool_name=name,
            payload=resolved_payload,
            context=replace(resolved_context, request_id=_resolve_request_id(resolved_context.request_id)),
            definition={"side_effect": "unknown"},
            policy_decision=resolved_policy_decision,
            allowed_tools=normalized_allowed_tools,
            timeout_seconds=timeout_seconds,
        )
        _append_audit(state, "tool.invoke.failed", code="UNKNOWN_TOOL")
        return _attach_middleware_metadata(
            _error_result(name, "UNKNOWN_TOOL", str(exc)),
            state,
        )

    state = ToolExecutionState(
        tool_name=name,
        payload=resolved_payload,
        context=resolved_context,
        definition=definition,
        policy_decision=resolved_policy_decision,
        allowed_tools=normalized_allowed_tools,
        timeout_seconds=timeout_seconds,
    )
    for middleware in middlewares or DEFAULT_TOOL_MIDDLEWARES:
        middleware(state)
        if state.blocked_result is not None:
            _append_audit(
                state,
                "tool.invoke.blocked",
                code=str(state.blocked_result.get("error", {}).get("code", "BLOCKED")),
            )
            _route_pre_side_effect_mutation_executor_dry_run(state)
            return _attach_middleware_metadata(state.blocked_result, state)

    result = tool_registry_service.invoke_tool(name, resolved_payload, context=state.context)
    if result.get("ok") is True:
        _append_audit(state, "tool.invoke.completed")
    else:
        error = result.get("error") if isinstance(result.get("error"), dict) else {}
        _append_audit(state, "tool.invoke.failed", code=str(error.get("code", "ERROR")))
    return _attach_middleware_metadata(result, state)
