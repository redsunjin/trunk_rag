from __future__ import annotations

from services import tool_trace_service


def test_build_execution_trace_captures_success_routing_seed():
    trace = tool_trace_service.build_execution_trace(
        request_id="req-1",
        actor="tester",
        tool_name="search_docs",
        side_effect="read",
        allow_mutation=False,
        allowed_tools=["search_docs"],
        timeout_seconds=5.0,
        elapsed_ms=12,
        middleware_steps=[
            {"middleware": "request_id", "status": "ok", "elapsed_ms": 1},
            {"middleware": "audit_log", "status": "ok", "elapsed_ms": 2},
        ],
        audit_events=[{"event": "tool.invoke.completed", "request_id": "req-1"}],
        result={
            "tool": "search_docs",
            "ok": True,
            "result": {
                "query_profile": "sample_pack",
                "collections": ["fr"],
                "route_reason": "compatibility_keyword",
                "budget_profile": "verified_local_single",
                "sources": [{"source": "fr.md"}],
            },
            "error": None,
        },
    )

    assert trace["schema_version"] == tool_trace_service.TRACE_SCHEMA_VERSION
    assert trace["request_id"] == "req-1"
    assert trace["runtime"]["timeout_seconds"] == 5.0
    assert trace["policy"]["allowed_tools"] == ["search_docs"]
    assert trace["tool"]["name"] == "search_docs"
    assert trace["tool"]["result_seed"]["source_count"] == 1
    assert trace["routing"]["route_reason"] == "compatibility_keyword"
    assert trace["outcome"] == {"ok": True, "error": None}
    assert trace["middleware"]["blocked_by"] is None


def test_build_execution_trace_captures_blocked_middleware_and_error():
    trace = tool_trace_service.build_execution_trace(
        request_id="req-2",
        actor="internal",
        tool_name="reindex",
        side_effect="write",
        allow_mutation=False,
        allowed_tools=None,
        timeout_seconds=30.0,
        elapsed_ms=3,
        middleware_steps=[
            {"middleware": "request_id", "status": "ok", "elapsed_ms": 1},
            {"middleware": "unsafe_action_guard", "status": "blocked", "elapsed_ms": 2},
        ],
        audit_events=[{"event": "tool.invoke.blocked", "code": "MUTATION_NOT_ALLOWED"}],
        result={
            "tool": "reindex",
            "ok": False,
            "result": None,
            "error": {
                "code": "MUTATION_NOT_ALLOWED",
                "message": "This tool requires ToolContext.allow_mutation=True.",
            },
        },
    )

    assert trace["tool"]["side_effect"] == "write"
    assert trace["policy"]["allow_mutation"] is False
    assert trace["middleware"]["blocked_by"] == "unsafe_action_guard"
    assert trace["outcome"]["ok"] is False
    assert trace["outcome"]["error"]["code"] == "MUTATION_NOT_ALLOWED"
