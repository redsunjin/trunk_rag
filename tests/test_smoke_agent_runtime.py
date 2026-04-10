from __future__ import annotations

from scripts import smoke_agent_runtime


def test_smoke_agent_runtime_checks_read_success_and_write_block(monkeypatch):
    calls = []

    def fake_run_agent_entry(request):
        calls.append(request)
        if request.tool_name == "health_check":
            return {
                "ok": True,
                "entry": {"selected_tool": "health_check"},
                "error": None,
                "execution_trace": {
                    "request_id": request.request_id,
                    "middleware": {"blocked_by": None},
                },
            }
        return {
            "ok": False,
            "entry": {"selected_tool": "reindex"},
            "error": {"code": "TOOL_NOT_ALLOWED"},
            "execution_trace": {
                "request_id": request.request_id,
                "middleware": {"blocked_by": "tool_allowlist"},
            },
        }

    monkeypatch.setattr(smoke_agent_runtime, "load_project_env", lambda: None)
    monkeypatch.setattr(smoke_agent_runtime.agent_runtime_service, "run_agent_entry", fake_run_agent_entry)

    result = smoke_agent_runtime.run_smoke()

    assert result["ok"] is True
    assert [call.tool_name for call in calls] == ["health_check", "reindex"]
    assert result["checks"][0]["summary"]["selected_tool"] == "health_check"
    assert result["checks"][1]["summary"]["error_code"] == "TOOL_NOT_ALLOWED"
    assert result["checks"][1]["summary"]["blocked_by"] == "tool_allowlist"


def test_smoke_agent_runtime_fails_when_write_tool_is_not_blocked(monkeypatch):
    def fake_run_agent_entry(request):
        return {
            "ok": True,
            "entry": {"selected_tool": request.tool_name},
            "error": None,
            "execution_trace": {
                "request_id": request.request_id,
                "middleware": {"blocked_by": None},
            },
        }

    monkeypatch.setattr(smoke_agent_runtime, "load_project_env", lambda: None)
    monkeypatch.setattr(smoke_agent_runtime.agent_runtime_service, "run_agent_entry", fake_run_agent_entry)

    result = smoke_agent_runtime.run_smoke()

    assert result["ok"] is False
    assert result["checks"][0]["ok"] is True
    assert result["checks"][1]["ok"] is False
