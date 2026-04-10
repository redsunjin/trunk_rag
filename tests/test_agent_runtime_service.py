from __future__ import annotations

from services import agent_runtime_service


def test_agent_entry_defaults_single_input_to_search_docs(monkeypatch):
    captured = {}

    def fake_invoke_tool_with_middlewares(name, payload, *, context=None, allowed_tools=None, timeout_seconds=None):
        captured["name"] = name
        captured["payload"] = payload
        captured["context"] = context
        captured["allowed_tools"] = allowed_tools
        captured["timeout_seconds"] = timeout_seconds
        return {
            "tool": name,
            "ok": True,
            "result": {"context": "sample"},
            "error": None,
            "execution_trace": {
                "schema_version": "v1.5.tool_execution_trace.v1",
                "request_id": "agent-1",
                "outcome": {"ok": True, "error": None},
            },
        }

    monkeypatch.setattr(agent_runtime_service.tool_middleware_service, "invoke_tool_with_middlewares", fake_invoke_tool_with_middlewares)

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="프랑스 과학 인재 양성을 요약해줘.",
            request_id="agent-1",
            timeout_seconds=8,
        )
    )

    assert result["ok"] is True
    assert result["entry"]["mode"] == "single_tool_draft"
    assert result["entry"]["selected_tool"] == "search_docs"
    assert captured["name"] == "search_docs"
    assert captured["payload"] == {"query": "프랑스 과학 인재 양성을 요약해줘."}
    assert captured["context"].request_id == "agent-1"
    assert captured["context"].actor == "internal_agent"
    assert captured["context"].timeout_seconds == 8
    assert "search_docs" in captured["allowed_tools"]
    assert result["execution_trace"]["request_id"] == "agent-1"


def test_agent_entry_rejects_empty_input_without_tool_call(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("tool middleware must not run for empty agent input")

    monkeypatch.setattr(agent_runtime_service.tool_middleware_service, "invoke_tool_with_middlewares", fail_if_invoked)

    result = agent_runtime_service.run_agent_entry(agent_runtime_service.AgentRuntimeRequest(input=" "))

    assert result["ok"] is False
    assert result["tool_call"] is None
    assert result["execution_trace"] is None
    assert result["error"]["code"] == "INVALID_AGENT_INPUT"


def test_agent_entry_forwards_explicit_tool_payload(monkeypatch):
    captured = {}

    def fake_invoke_tool_with_middlewares(name, payload, *, context=None, allowed_tools=None, timeout_seconds=None):
        captured["name"] = name
        captured["payload"] = payload
        captured["allowed_tools"] = allowed_tools
        return {
            "tool": name,
            "ok": True,
            "result": {"origin": "seed"},
            "error": None,
            "execution_trace": {"request_id": "doc-1", "outcome": {"ok": True, "error": None}},
        }

    monkeypatch.setattr(agent_runtime_service.tool_middleware_service, "invoke_tool_with_middlewares", fake_invoke_tool_with_middlewares)

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="프랑스 문서를 읽어줘.",
            tool_name="read_doc",
            tool_payload={"collection": "fr", "doc_key": "fr"},
            request_id="doc-1",
        )
    )

    assert result["ok"] is True
    assert captured["name"] == "read_doc"
    assert captured["payload"] == {"collection": "fr", "doc_key": "fr"}
    assert "read_doc" in captured["allowed_tools"]


def test_agent_entry_uses_read_only_allowlist_by_default():
    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="전체 인덱스를 갱신해줘.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            request_id="agent-write-1",
        )
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_ALLOWED"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "tool_allowlist"
