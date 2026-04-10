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


def _sample_trace_with_sensitive_fields():
    return {
        "schema_version": tool_trace_service.TRACE_SCHEMA_VERSION,
        "request_id": "req-sensitive",
        "actor": "admin@example.test",
        "runtime": {"timeout_seconds": 30.0, "elapsed_ms": 17},
        "policy": {"allow_mutation": False, "allowed_tools": ["search_docs"]},
        "tool": {
            "name": "search_docs",
            "side_effect": "read",
            "result_seed": {
                "origin": "managed",
                "collection_key": "all",
                "doc_key": "contract-secret",
                "source_name": "/tmp/private/contract-secret.md",
                "source_count": 2,
                "content": "raw document body",
            },
        },
        "routing": {
            "query_profile": "generic",
            "collections": ["all"],
            "route_reason": "default",
            "budget_profile": "verified_local_single",
        },
        "middleware": {
            "blocked_by": None,
            "steps": [
                {
                    "middleware": "request_id",
                    "status": "ok",
                    "elapsed_ms": 1,
                    "detail": {
                        "request_id": "req-sensitive",
                        "payload": {"query": "raw user query"},
                        "local_path": "/tmp/private/contract-secret.md",
                    },
                }
            ],
        },
        "outcome": {
            "ok": False,
            "error": {
                "code": "HTTP_ERROR",
                "status_code": 500,
                "message": "full stack trace with /tmp/private/path",
            },
        },
        "audit": {
            "events": [
                {
                    "event": "tool.invoke.failed",
                    "tool": "search_docs",
                    "actor": "admin@example.test",
                    "elapsed_ms": 17,
                    "admin_code": "secret",
                    "code": "HTTP_ERROR",
                }
            ]
        },
        "raw_payload": {"query": "raw user query", "admin_code": "secret"},
    }


def test_redact_execution_trace_public_profile_keeps_minimal_safe_fields():
    redacted = tool_trace_service.redact_execution_trace(
        _sample_trace_with_sensitive_fields(),
        audience="public",
    )

    assert redacted["schema_version"] == tool_trace_service.TRACE_REDACTION_SCHEMA_VERSION
    assert redacted["source_schema_version"] == tool_trace_service.TRACE_SCHEMA_VERSION
    assert redacted["audience"] == "public"
    assert redacted["request_id"] == "req-sensitive"
    assert redacted["tool"] == {"name": "search_docs", "side_effect": "read"}
    assert redacted["outcome"]["error"] == {"code": "HTTP_ERROR", "status_code": 500}
    assert redacted["middleware"] == {"blocked_by": None}
    assert "actor" not in redacted
    assert "audit" not in redacted
    assert "steps" not in redacted["middleware"]
    assert "raw_payload" not in redacted


def test_redact_execution_trace_persisted_profile_keeps_diagnostic_seed_only():
    redacted = tool_trace_service.redact_execution_trace(
        _sample_trace_with_sensitive_fields(),
        audience="persisted",
    )

    assert redacted["audience"] == "persisted"
    assert redacted["tool"]["result_seed"] == {
        "origin": "managed",
        "collection_key": "all",
        "source_count": 2,
    }
    assert redacted["middleware"]["steps"] == [
        {"middleware": "request_id", "status": "ok", "elapsed_ms": 1}
    ]
    assert redacted["audit"]["events"] == [
        {
            "event": "tool.invoke.failed",
            "elapsed_ms": 17,
            "code": "HTTP_ERROR",
            "tool": "search_docs",
        }
    ]
    assert redacted["outcome"]["error"] == {"code": "HTTP_ERROR", "status_code": 500}


def test_redact_execution_trace_internal_profile_still_removes_raw_content_and_secrets():
    redacted = tool_trace_service.redact_execution_trace(
        _sample_trace_with_sensitive_fields(),
        audience="internal",
    )

    assert redacted["audience"] == "internal"
    assert redacted["actor"] == "admin@example.test"
    assert redacted["tool"]["result_seed"] == {
        "origin": "managed",
        "collection_key": "all",
        "doc_key": "contract-secret",
        "source_name": "/tmp/private/contract-secret.md",
        "source_count": 2,
    }
    assert redacted["middleware"]["steps"][0]["detail"] == {"request_id": "req-sensitive"}
    assert redacted["outcome"]["error"] == {
        "code": "HTTP_ERROR",
        "status_code": 500,
        "message": "[redacted]",
    }
    assert "admin_code" not in redacted["audit"]["events"][0]
    assert "raw_payload" not in redacted


def test_redact_execution_trace_rejects_unknown_audience():
    try:
        tool_trace_service.redact_execution_trace({}, audience="external")
    except ValueError as exc:
        assert "unsupported trace audience" in str(exc)
    else:
        raise AssertionError("expected unsupported audience to fail")
