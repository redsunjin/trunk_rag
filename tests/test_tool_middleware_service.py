from __future__ import annotations

from services import tool_middleware_service
from services.tool_registry_service import ToolContext


def test_tool_middleware_wraps_read_tool_with_request_id_budget_and_audit():
    result = tool_middleware_service.invoke_tool_with_middlewares(
        "read_doc",
        {"collection": "fr", "doc_key": "fr"},
        context=ToolContext(request_id="", actor="tester"),
        allowed_tools=("read_doc",),
        timeout_seconds=12,
    )

    assert result["ok"] is True
    assert result["result"]["origin"] == "seed"
    assert result["middleware"]["request_id"].startswith("tool-")
    assert result["middleware"]["actor"] == "tester"
    assert result["middleware"]["timeout_seconds"] == 12.0
    assert result["middleware"]["allowed_tools"] == ["read_doc"]
    assert [item["middleware"] for item in result["middleware"]["trace"]] == [
        "request_id",
        "timeout_budget",
        "tool_allowlist",
        "unsafe_action_guard",
        "audit_log",
    ]
    assert [item["event"] for item in result["middleware"]["audit_log"]] == [
        "tool.invoke.requested",
        "tool.invoke.completed",
    ]


def test_tool_allowlist_blocks_before_adapter(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("adapter must not be called when allowlist blocks")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "read_doc",
        {"collection": "fr", "doc_key": "fr"},
        allowed_tools=("health_check",),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_ALLOWED"
    assert result["middleware"]["audit_log"][-1]["event"] == "tool.invoke.blocked"


def test_unsafe_action_guard_blocks_write_without_mutation_context(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called without mutation context")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares("reindex", {"collection": "all"})

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_NOT_ALLOWED"
    assert result["middleware"]["trace"][-1]["middleware"] == "unsafe_action_guard"
    assert result["middleware"]["trace"][-1]["status"] == "blocked"


def test_mutation_context_and_timeout_budget_are_passed_to_registry(monkeypatch):
    captured = {}

    def fake_invoke_tool(name, payload, *, context=None):
        captured["name"] = name
        captured["payload"] = payload
        captured["context"] = context
        return {"tool": name, "ok": True, "result": {"status": "queued"}, "error": None}

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fake_invoke_tool)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(request_id="req-1", actor="admin", allow_mutation=True),
        allowed_tools=("reindex",),
        timeout_seconds=7,
    )

    assert result["ok"] is True
    assert captured["name"] == "reindex"
    assert captured["payload"] == {"collection": "all"}
    assert captured["context"].request_id == "req-1"
    assert captured["context"].actor == "admin"
    assert captured["context"].allow_mutation is True
    assert captured["context"].timeout_seconds == 7.0
    assert result["middleware"]["audit_log"][-1]["event"] == "tool.invoke.completed"


def test_custom_middlewares_run_in_sequence(monkeypatch):
    calls = []

    def first(state):
        calls.append("first")
        tool_middleware_service.request_id_middleware(state)

    def second(state):
        calls.append("second")
        tool_middleware_service.audit_log_middleware(state)

    monkeypatch.setattr(
        tool_middleware_service.tool_registry_service,
        "invoke_tool",
        lambda name, payload, *, context=None: {
            "tool": name,
            "ok": True,
            "result": {"request_id": context.request_id},
            "error": None,
        },
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "health_check",
        middlewares=(first, second),
    )

    assert result["ok"] is True
    assert calls == ["first", "second"]
    assert [item["middleware"] for item in result["middleware"]["trace"]] == ["request_id", "audit_log"]
