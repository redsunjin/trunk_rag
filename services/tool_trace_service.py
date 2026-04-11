from __future__ import annotations

TRACE_SCHEMA_VERSION = "v1.5.tool_execution_trace.v1"
TRACE_REDACTION_SCHEMA_VERSION = "v1.5.tool_execution_trace.redacted.v1"

TRACE_AUDIENCE_INTERNAL = "internal"
TRACE_AUDIENCE_PUBLIC = "public"
TRACE_AUDIENCE_PERSISTED = "persisted"

_SUPPORTED_TRACE_AUDIENCES = {
    TRACE_AUDIENCE_INTERNAL,
    TRACE_AUDIENCE_PUBLIC,
    TRACE_AUDIENCE_PERSISTED,
}


def _copy_dict_items(items: list[dict[str, object]]) -> list[dict[str, object]]:
    return [dict(item) for item in items]


def _extract_error(error: object) -> dict[str, object] | None:
    if not isinstance(error, dict):
        return None
    extracted: dict[str, object] = {}
    for key in ("code", "status_code", "message"):
        if key in error:
            extracted[key] = error[key]
    return extracted or dict(error)


def _extract_result_payload(result: dict[str, object]) -> dict[str, object]:
    payload = result.get("result")
    if isinstance(payload, dict):
        return payload
    return {}


def _extract_routing_seed(result: dict[str, object]) -> dict[str, object]:
    payload = _extract_result_payload(result)
    return {
        "query_profile": payload.get("query_profile"),
        "collections": payload.get("collections"),
        "route_reason": payload.get("route_reason"),
        "budget_profile": payload.get("budget_profile"),
    }


def _extract_result_seed(result: dict[str, object]) -> dict[str, object]:
    payload = _extract_result_payload(result)
    seed: dict[str, object] = {}
    for key in ("origin", "collection_key", "doc_key", "source_name", "status"):
        if key in payload:
            seed[key] = payload[key]
    if "sources" in payload:
        sources = payload["sources"]
        seed["source_count"] = len(sources) if isinstance(sources, list) else 0
    return seed


def _find_blocked_by(middleware_steps: list[dict[str, object]]) -> str | None:
    for step in reversed(middleware_steps):
        if step.get("status") == "blocked":
            return str(step.get("middleware", "unknown"))
    return None


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def _compact_error(error: object, *, include_message: bool = False) -> dict[str, object] | None:
    if not isinstance(error, dict):
        return None
    compact: dict[str, object] = {}
    for key in ("code", "status_code"):
        if key in error:
            compact[key] = error[key]
    if include_message and "message" in error:
        compact["message"] = "[redacted]"
    return compact or None


def _redact_middleware_steps(steps: object, *, include_detail: bool) -> list[dict[str, object]]:
    redacted: list[dict[str, object]] = []
    for step in _safe_list_of_dicts(steps):
        item: dict[str, object] = {
            "middleware": step.get("middleware"),
            "status": step.get("status"),
            "elapsed_ms": step.get("elapsed_ms"),
        }
        if include_detail and isinstance(step.get("detail"), dict):
            detail = {
                key: value
                for key, value in dict(step["detail"]).items()
                if key
                in {
                    "request_id",
                    "timeout_seconds",
                    "allowed_tools",
                    "side_effect",
                    "allow_mutation",
                    "actor_category",
                    "requires_admin_auth",
                    "admin_authenticated",
                    "requires_mutation_intent",
                    "mutation_intent_present",
                    "requires_preview_before_apply",
                }
            }
            if detail:
                item["detail"] = detail
        redacted.append(item)
    return redacted


def _redact_audit_events(events: object, *, include_actor: bool) -> list[dict[str, object]]:
    redacted: list[dict[str, object]] = []
    for event in _safe_list_of_dicts(events):
        item: dict[str, object] = {
            "event": event.get("event"),
            "elapsed_ms": event.get("elapsed_ms"),
        }
        if "code" in event:
            item["code"] = event["code"]
        if "tool" in event:
            item["tool"] = event["tool"]
        if include_actor and "actor" in event:
            item["actor"] = event["actor"]
        redacted.append(item)
    return redacted


def _redact_result_seed(result_seed: object, *, include_conditional: bool) -> dict[str, object]:
    seed = _safe_dict(result_seed)
    if not seed:
        return {}
    keys = {"origin", "collection_key", "source_count"}
    if include_conditional:
        keys.update({"doc_key", "source_name", "status"})
    return {key: seed[key] for key in keys if key in seed}


def _redact_common_trace(trace: dict[str, object], *, include_actor: bool) -> dict[str, object]:
    runtime = _safe_dict(trace.get("runtime"))
    policy = _safe_dict(trace.get("policy"))
    tool = _safe_dict(trace.get("tool"))
    routing = _safe_dict(trace.get("routing"))
    middleware = _safe_dict(trace.get("middleware"))
    outcome = _safe_dict(trace.get("outcome"))
    redacted: dict[str, object] = {
        "schema_version": TRACE_REDACTION_SCHEMA_VERSION,
        "source_schema_version": trace.get("schema_version"),
        "audience": TRACE_AUDIENCE_PUBLIC,
        "request_id": trace.get("request_id"),
        "runtime": {
            "timeout_seconds": runtime.get("timeout_seconds"),
            "elapsed_ms": runtime.get("elapsed_ms"),
        },
        "policy": {
            "allow_mutation": policy.get("allow_mutation"),
            "allowed_tools": policy.get("allowed_tools"),
            "actor_category": policy.get("actor_category"),
            "mutation_candidate_tools": policy.get("mutation_candidate_tools"),
            "requires_admin_auth": policy.get("requires_admin_auth"),
            "requires_mutation_intent": policy.get("requires_mutation_intent"),
            "requires_preview_before_apply": policy.get("requires_preview_before_apply"),
            "audit_scope": policy.get("audit_scope"),
            "used_fallback": policy.get("used_fallback"),
        },
        "tool": {
            "name": tool.get("name"),
            "side_effect": tool.get("side_effect"),
        },
        "routing": {
            "query_profile": routing.get("query_profile"),
            "collections": routing.get("collections"),
            "route_reason": routing.get("route_reason"),
            "budget_profile": routing.get("budget_profile"),
        },
        "middleware": {
            "blocked_by": middleware.get("blocked_by"),
        },
        "outcome": {
            "ok": outcome.get("ok") is True,
            "error": _compact_error(outcome.get("error")),
        },
    }
    if include_actor:
        redacted["actor"] = trace.get("actor")
    return redacted


def redact_execution_trace(
    trace: dict[str, object],
    *,
    audience: str,
) -> dict[str, object]:
    normalized_audience = (audience or "").strip().lower()
    if normalized_audience not in _SUPPORTED_TRACE_AUDIENCES:
        raise ValueError(f"unsupported trace audience: {audience}")
    if not isinstance(trace, dict):
        raise TypeError("trace must be an object.")

    if normalized_audience == TRACE_AUDIENCE_PUBLIC:
        return _redact_common_trace(trace, include_actor=False)

    include_internal_detail = normalized_audience == TRACE_AUDIENCE_INTERNAL
    redacted = _redact_common_trace(trace, include_actor=include_internal_detail)
    redacted["audience"] = normalized_audience

    tool = _safe_dict(trace.get("tool"))
    redacted["tool"] = {
        **_safe_dict(redacted.get("tool")),
        "result_seed": _redact_result_seed(
            tool.get("result_seed"),
            include_conditional=include_internal_detail,
        ),
    }

    middleware = _safe_dict(trace.get("middleware"))
    redacted["middleware"] = {
        **_safe_dict(redacted.get("middleware")),
        "steps": _redact_middleware_steps(
            middleware.get("steps"),
            include_detail=include_internal_detail,
        ),
    }

    audit = _safe_dict(trace.get("audit"))
    redacted["audit"] = {
        "events": _redact_audit_events(
            audit.get("events"),
            include_actor=include_internal_detail,
        )
    }

    outcome = _safe_dict(trace.get("outcome"))
    redacted["outcome"] = {
        "ok": outcome.get("ok") is True,
        "error": _compact_error(
            outcome.get("error"),
            include_message=include_internal_detail,
        ),
    }
    return redacted


def build_execution_trace(
    *,
    request_id: str,
    actor: str,
    tool_name: str,
    side_effect: str,
    allow_mutation: bool,
    allowed_tools: list[str] | None,
    policy_details: dict[str, object] | None,
    timeout_seconds: float | None,
    elapsed_ms: int,
    middleware_steps: list[dict[str, object]],
    audit_events: list[dict[str, object]],
    result: dict[str, object],
) -> dict[str, object]:
    steps = _copy_dict_items(middleware_steps)
    events = _copy_dict_items(audit_events)
    error = _extract_error(result.get("error"))
    return {
        "schema_version": TRACE_SCHEMA_VERSION,
        "request_id": request_id,
        "actor": actor,
        "runtime": {
            "timeout_seconds": timeout_seconds,
            "elapsed_ms": elapsed_ms,
        },
        "policy": {
            "allow_mutation": allow_mutation,
            "allowed_tools": list(allowed_tools) if allowed_tools is not None else None,
            "actor_category": _safe_dict(policy_details).get("actor_category"),
            "read_allowed_tools": _safe_dict(policy_details).get("read_allowed_tools"),
            "mutation_candidate_tools": _safe_dict(policy_details).get("mutation_candidate_tools"),
            "effective_allowed_tools": _safe_dict(policy_details).get("effective_allowed_tools"),
            "requires_admin_auth": _safe_dict(policy_details).get("requires_admin_auth"),
            "requires_mutation_intent": _safe_dict(policy_details).get("requires_mutation_intent"),
            "requires_preview_before_apply": _safe_dict(policy_details).get("requires_preview_before_apply"),
            "audit_scope": _safe_dict(policy_details).get("audit_scope"),
            "source_schema_version": _safe_dict(policy_details).get("source_schema_version"),
            "used_fallback": _safe_dict(policy_details).get("used_fallback"),
        },
        "tool": {
            "name": tool_name,
            "side_effect": side_effect or "unknown",
            "result_seed": _extract_result_seed(result),
        },
        "routing": _extract_routing_seed(result),
        "middleware": {
            "blocked_by": _find_blocked_by(steps),
            "steps": steps,
        },
        "outcome": {
            "ok": result.get("ok") is True,
            "error": error,
        },
        "audit": {
            "events": events,
        },
    }
