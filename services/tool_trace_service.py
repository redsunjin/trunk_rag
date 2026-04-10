from __future__ import annotations

TRACE_SCHEMA_VERSION = "v1.5.tool_execution_trace.v1"


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


def build_execution_trace(
    *,
    request_id: str,
    actor: str,
    tool_name: str,
    side_effect: str,
    allow_mutation: bool,
    allowed_tools: list[str] | None,
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
