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
                    "contracts": {
                        "audit_sink": {
                            "sink_type": "null_append_only",
                            "sequence_id": None,
                            "storage_path": None,
                            "retention_days": None,
                            "prune_policy": None,
                        }
                    },
                },
            }
        error_code = {
            "agent-smoke-write-read-only": "TOOL_NOT_ALLOWED",
            "agent-smoke-auth": "ADMIN_AUTH_REQUIRED",
            "agent-smoke-intent": "MUTATION_INTENT_REQUIRED",
            "agent-smoke-preview": "PREVIEW_REQUIRED",
            "agent-smoke-apply": "MUTATION_APPLY_NOT_ENABLED",
        }[request.request_id]
        error = {"code": error_code}
        contracts = {
            "audit_sink": {
                "sink_type": "null_append_only",
                "sequence_id": None,
                "storage_path": None,
                "retention_days": None,
                "prune_policy": None,
            }
        }
        if request.request_id in {"agent-smoke-preview", "agent-smoke-apply"}:
            apply_envelope = {
                "schema_version": "v1.5.mutation_apply_envelope.v1",
                "preview_ref": {
                    "tool_name": "reindex",
                    "target": {"collection_key": "all"},
                },
                "audit_ref": {
                    "sink_type": "null_append_only",
                    "sequence_id": None,
                },
                "apply_control": {
                    "execution_enabled": False,
                },
            }
            error["apply_envelope"] = apply_envelope
            contracts["apply_envelope"] = apply_envelope
        if request.request_id == "agent-smoke-apply":
            mutation_executor = {
                "executor_name": "noop_mutation_executor",
                "selection_state": "noop_fallback",
                "selection_reason": "activation_guard_blocked",
                "activation_requested": False,
                "execution_enabled": False,
                "activation": {
                    "blocked_by": ["activation_not_requested", "durable_audit_not_ready"],
                    "audit_sink_type": "null_append_only",
                    "audit_sequence_id": None,
                },
                "boundary": {
                    "family": "reindex",
                    "classification": "derivative_runtime_state",
                },
            }
            error["mutation_executor"] = mutation_executor
            contracts["mutation_executor"] = mutation_executor
        return {
            "ok": False,
            "entry": {"selected_tool": "reindex"},
            "error": error,
            "execution_trace": {
                "request_id": request.request_id,
                "middleware": {
                    "blocked_by": (
                        "tool_allowlist"
                        if error_code == "TOOL_NOT_ALLOWED"
                        else "mutation_apply_guard"
                        if error_code == "MUTATION_APPLY_NOT_ENABLED"
                        else "mutation_policy_guard"
                    )
                },
                "contracts": contracts,
            },
        }

    monkeypatch.setattr(smoke_agent_runtime, "load_project_env", lambda: None)
    monkeypatch.setattr(smoke_agent_runtime.agent_runtime_service, "run_agent_entry", fake_run_agent_entry)

    result = smoke_agent_runtime.run_smoke()

    assert result["ok"] is True
    assert result["schema_version"] == smoke_agent_runtime.MUTATION_ACTIVATION_SMOKE_SCHEMA_VERSION
    assert result["requested_live_binding"] is False
    assert [call.tool_name for call in calls] == [
        "health_check",
        "reindex",
        "reindex",
        "reindex",
        "reindex",
        "reindex",
    ]
    assert result["checks"][0]["summary"]["selected_tool"] == "health_check"
    assert result["checks"][1]["summary"]["error_code"] == "TOOL_NOT_ALLOWED"
    assert result["checks"][1]["summary"]["blocked_by"] == "tool_allowlist"
    assert result["checks"][2]["summary"]["error_code"] == "ADMIN_AUTH_REQUIRED"
    assert result["checks"][3]["summary"]["error_code"] == "MUTATION_INTENT_REQUIRED"
    assert result["checks"][4]["summary"]["error_code"] == "PREVIEW_REQUIRED"
    assert result["checks"][4]["summary"]["apply_envelope"] == {
        "schema_version": "v1.5.mutation_apply_envelope.v1",
        "preview_tool_name": "reindex",
        "preview_target": {"collection_key": "all"},
        "audit_sink_type": "null_append_only",
        "audit_sequence_id": None,
        "execution_enabled": False,
    }
    assert result["checks"][5]["summary"]["error_code"] == "MUTATION_APPLY_NOT_ENABLED"
    assert result["checks"][5]["summary"]["blocked_by"] == "mutation_apply_guard"
    assert result["checks"][5]["summary"]["audit_sink"] == {
        "sink_type": "null_append_only",
        "sequence_id": None,
        "storage_path": None,
        "retention_days": None,
        "prune_policy": None,
    }
    assert result["checks"][5]["summary"]["mutation_executor"] == {
        "executor_name": "noop_mutation_executor",
        "selection_state": "noop_fallback",
        "selection_reason": "activation_guard_blocked",
        "activation_requested": False,
        "execution_enabled": False,
        "activation_blocked_by": ["activation_not_requested", "durable_audit_not_ready"],
        "audit_sink_type": "null_append_only",
        "audit_sequence_id": None,
        "boundary_family": "reindex",
        "boundary_classification": "derivative_runtime_state",
    }


def test_smoke_agent_runtime_opt_in_live_binding_injects_executor_binding(monkeypatch):
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
                    "contracts": {},
                },
            }
        if request.request_id == "agent-smoke-preview":
            return {
                "ok": False,
                "entry": {"selected_tool": "reindex"},
                "error": {
                    "code": "PREVIEW_REQUIRED",
                    "apply_envelope": {
                        "schema_version": "v1.5.mutation_apply_envelope.v1",
                        "preview_ref": {
                            "tool_name": "reindex",
                            "target": {"collection_key": "all"},
                        },
                        "audit_ref": {
                            "sink_type": "null_append_only",
                            "sequence_id": None,
                        },
                        "apply_control": {
                            "execution_enabled": False,
                        },
                    },
                },
                "execution_trace": {
                    "request_id": request.request_id,
                    "middleware": {"blocked_by": "mutation_policy_guard"},
                    "contracts": {},
                },
            }
        error_codes = {
            "agent-smoke-write-read-only": "TOOL_NOT_ALLOWED",
            "agent-smoke-auth": "ADMIN_AUTH_REQUIRED",
            "agent-smoke-intent": "MUTATION_INTENT_REQUIRED",
            "agent-smoke-apply": "MUTATION_APPLY_NOT_ENABLED",
        }
        error_code = error_codes[request.request_id]
        blocked_by = "mutation_apply_guard" if error_code == "MUTATION_APPLY_NOT_ENABLED" else "mutation_policy_guard"
        if error_code == "TOOL_NOT_ALLOWED":
            blocked_by = "tool_allowlist"
        return {
            "ok": False,
            "entry": {"selected_tool": "reindex"},
            "error": {"code": error_code},
            "execution_trace": {
                "request_id": request.request_id,
                "middleware": {"blocked_by": blocked_by},
                "contracts": {},
            },
        }

    monkeypatch.setattr(smoke_agent_runtime, "load_project_env", lambda: None)
    monkeypatch.setattr(smoke_agent_runtime.agent_runtime_service, "run_agent_entry", fake_run_agent_entry)

    result = smoke_agent_runtime.run_smoke(opt_in_live_binding=True)

    assert result["requested_live_binding"] is True
    apply_request = calls[-1]
    assert apply_request.request_id == "agent-smoke-apply"
    assert apply_request.executor_binding == {
        "binding_kind": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
        "binding_source": smoke_agent_runtime.MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE,
        "executor_name": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
    }


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
    assert result["schema_version"] == smoke_agent_runtime.MUTATION_ACTIVATION_SMOKE_SCHEMA_VERSION
    assert result["checks"][0]["ok"] is True
    assert result["checks"][1]["ok"] is False
