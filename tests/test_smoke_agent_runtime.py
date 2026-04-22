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
    assert result["requested_live_binding_stage"] is None
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
    assert result["requested_live_binding_stage"] is None
    apply_request = calls[-1]
    assert apply_request.request_id == "agent-smoke-apply"
    assert apply_request.executor_binding == {
        "binding_kind": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
        "binding_source": smoke_agent_runtime.MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE,
        "executor_name": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
    }


def test_smoke_agent_runtime_opt_in_live_binding_concrete_stage_injects_executor_result_binding(monkeypatch):
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
                            "target": {"collection_key": "all", "include_compatibility_bundle": True},
                        },
                        "audit_ref": {
                            "sink_type": "local_file_append_only",
                            "sequence_id": 7,
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
        error = {"code": "MUTATION_APPLY_NOT_ENABLED"}
        contracts = {}
        if request.request_id == "agent-smoke-apply":
            mutation_executor = {
                "executor_name": "reindex_mutation_adapter_live",
                "selection_state": "live_result_skeleton",
                "selection_reason": "explicit_live_result_contract_requested",
                "activation_requested": True,
                "execution_enabled": True,
                "activation": {
                    "blocked_by": [],
                    "audit_sink_type": "local_file_append_only",
                    "audit_sequence_id": 7,
                },
                "boundary": {
                    "family": "reindex",
                    "classification": "derivative_runtime_state",
                },
            }
            mutation_executor_result = {
                "schema_version": "v1.5.reindex_live_adapter_result.v1",
                "reindex_summary": {
                    "collection_key": "all",
                    "operation": "rebuild_vector_index",
                    "requested_reset": True,
                    "requested_compatibility_bundle": True,
                },
                "audit_receipt_ref": {
                    "sequence_id": 7,
                    "storage_path": "/tmp/mutation-audit/audit-20260421.jsonl",
                },
                "rollback_hint": {
                    "mode": "rebuild_from_source_documents",
                    "collection_key": "all",
                },
            }
            mutation_success_promotion = {
                "schema_version": "v1.5.reindex_live_adapter_success_promotion.v1",
                "promotion_state": "draft_ready_not_enabled",
                "current_surface": {
                    "kind": "blocked_success_sidecar",
                    "result_location": "error.mutation_executor_result",
                },
                "future_success_surface": {
                    "kind": "top_level_apply_success",
                    "result_location": "result",
                    "top_level_ok": True,
                },
                "promotion_gate": {
                    "actual_side_effect_enabled": False,
                },
            }
            mutation_top_level_promotion_router = {
                "schema_version": "v1.5.reindex_live_adapter_top_level_promotion_router.v1",
                "router_state": "draft_ready_not_enabled",
                "success_route": {
                    "eligible": True,
                    "target_result_location": "result",
                    "target_top_level_ok": True,
                },
                "failure_route": {
                    "target_error_location": "error",
                    "supported_codes": [
                        "REINDEX_TARGET_MISMATCH",
                        "REINDEX_AUDIT_LINKAGE_INVALID",
                        "REINDEX_RUNTIME_EXECUTION_FAILED",
                        "REINDEX_ROLLBACK_HINT_UNAVAILABLE",
                    ],
                },
                "promotion_gate": {
                    "top_level_promotion_enabled": False,
                    "actual_side_effect_enabled": False,
                },
            }
            error["mutation_executor"] = mutation_executor
            error["mutation_executor_result"] = mutation_executor_result
            error["mutation_success_promotion"] = mutation_success_promotion
            error["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
            contracts["mutation_executor"] = mutation_executor
            contracts["mutation_executor_result"] = mutation_executor_result
            contracts["mutation_success_promotion"] = mutation_success_promotion
            contracts["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
        return {
            "ok": False,
            "entry": {"selected_tool": "reindex"},
            "error": error,
            "execution_trace": {
                "request_id": request.request_id,
                "middleware": {
                    "blocked_by": (
                        "tool_allowlist"
                        if request.request_id == "agent-smoke-write-read-only"
                        else "mutation_apply_guard"
                        if request.request_id == "agent-smoke-apply"
                        else "mutation_policy_guard"
                    )
                },
                "contracts": contracts,
            },
        }

    monkeypatch.setattr(smoke_agent_runtime, "load_project_env", lambda: None)
    monkeypatch.setattr(smoke_agent_runtime.agent_runtime_service, "run_agent_entry", fake_run_agent_entry)

    result = smoke_agent_runtime.run_smoke(
        opt_in_live_binding=True,
        opt_in_live_binding_stage_concrete=True,
    )

    assert result["requested_live_binding"] is True
    assert (
        result["requested_live_binding_stage"]
        == smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON
    )
    apply_request = calls[-1]
    assert apply_request.request_id == "agent-smoke-apply"
    assert apply_request.executor_binding == {
        "binding_kind": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
        "binding_source": smoke_agent_runtime.MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE,
        "executor_name": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
        smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD: (
            smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON
        ),
    }
    assert result["checks"][5]["summary"]["mutation_executor_result"] == {
        "schema_version": "v1.5.reindex_live_adapter_result.v1",
        "collection_key": "all",
        "operation": "rebuild_vector_index",
        "requested_reset": True,
        "requested_compatibility_bundle": True,
        "audit_sequence_id": 7,
        "audit_storage_path": "/tmp/mutation-audit/audit-20260421.jsonl",
        "rollback_mode": "rebuild_from_source_documents",
        "rollback_collection_key": "all",
    }
    assert result["checks"][5]["summary"]["mutation_success_promotion"] == {
        "schema_version": "v1.5.reindex_live_adapter_success_promotion.v1",
        "promotion_state": "draft_ready_not_enabled",
        "current_kind": "blocked_success_sidecar",
        "current_result_location": "error.mutation_executor_result",
        "future_kind": "top_level_apply_success",
        "future_result_location": "result",
        "future_top_level_ok": True,
        "actual_side_effect_enabled": False,
    }
    assert result["checks"][5]["summary"]["mutation_top_level_promotion_router"] == {
        "schema_version": "v1.5.reindex_live_adapter_top_level_promotion_router.v1",
        "router_state": "draft_ready_not_enabled",
        "success_eligible": True,
        "success_target_result_location": "result",
        "success_target_top_level_ok": True,
        "failure_target_error_location": "error",
        "failure_code_count": 4,
        "top_level_promotion_enabled": False,
        "actual_side_effect_enabled": False,
    }


def test_smoke_agent_runtime_opt_in_live_binding_guarded_stage_injects_executor_binding(monkeypatch):
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
                            "sink_type": "local_file_append_only",
                            "sequence_id": 12,
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
        error = {"code": error_code}
        contracts = {}
        if request.request_id == "agent-smoke-apply":
            mutation_executor = {
                "executor_name": "reindex_mutation_adapter_live",
                "selection_state": "guarded_live_executor",
                "selection_reason": "explicit_guarded_live_executor_requested",
                "activation_requested": True,
                "execution_enabled": True,
                "actual_runtime_handler": "index_service.reindex",
                "actual_runtime_handler_invoked": True,
                "activation": {
                    "blocked_by": [],
                    "audit_sink_type": "local_file_append_only",
                    "audit_sequence_id": 12,
                },
                "boundary": {
                    "family": "reindex",
                    "classification": "derivative_runtime_state",
                },
            }
            mutation_executor_result = {
                "schema_version": "v1.5.reindex_live_adapter_result.v1",
                "reindex_summary": {
                    "collection_key": "all",
                    "operation": "rebuild_vector_index",
                    "requested_reset": True,
                    "requested_compatibility_bundle": False,
                    "runtime_chunks": 12,
                    "runtime_vectors": 34,
                    "runtime_scope": "default_runtime_only",
                },
                "audit_receipt_ref": {
                    "sequence_id": 12,
                    "storage_path": "/tmp/mutation-audit/audit-20260422.jsonl",
                },
                "rollback_hint": {
                    "mode": "rebuild_from_source_documents",
                    "collection_key": "all",
                },
                "runtime_result": {
                    "collection_key": "all",
                    "collection": "doc_rag_main",
                    "chunks": 12,
                    "vectors": 34,
                    "related_collection_keys": ["all"],
                    "reindex_scope": "default_runtime_only",
                },
            }
            mutation_top_level_promotion_router = {
                "schema_version": "v1.5.reindex_live_adapter_top_level_promotion_router.v1",
                "router_state": "draft_ready_not_enabled",
                "success_route": {
                    "eligible": True,
                    "target_result_location": "result",
                    "target_top_level_ok": True,
                },
                "failure_route": {
                    "target_error_location": "error",
                    "supported_codes": [],
                },
                "promotion_gate": {
                    "top_level_promotion_enabled": False,
                    "actual_side_effect_enabled": False,
                },
            }
            error["mutation_executor"] = mutation_executor
            error["mutation_executor_result"] = mutation_executor_result
            error["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
            contracts["mutation_executor"] = mutation_executor
            contracts["mutation_executor_result"] = mutation_executor_result
            contracts["mutation_top_level_promotion_router"] = mutation_top_level_promotion_router
        return {
            "ok": False,
            "entry": {"selected_tool": "reindex"},
            "error": error,
            "execution_trace": {
                "request_id": request.request_id,
                "middleware": {
                    "blocked_by": (
                        "tool_allowlist"
                        if request.request_id == "agent-smoke-write-read-only"
                        else "mutation_apply_guard"
                        if request.request_id == "agent-smoke-apply"
                        else "mutation_policy_guard"
                    )
                },
                "contracts": contracts,
            },
        }

    monkeypatch.setattr(smoke_agent_runtime, "load_project_env", lambda: None)
    monkeypatch.setattr(smoke_agent_runtime.agent_runtime_service, "run_agent_entry", fake_run_agent_entry)

    result = smoke_agent_runtime.run_smoke(
        opt_in_live_binding=True,
        opt_in_live_binding_stage_guarded=True,
    )

    assert result["ok"] is True
    assert result["requested_live_binding"] is True
    assert (
        result["requested_live_binding_stage"]
        == smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_GUARDED_LIVE_EXECUTOR
    )
    apply_request = calls[-1]
    assert apply_request.request_id == "agent-smoke-apply"
    assert apply_request.executor_binding == {
        "binding_kind": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
        "binding_source": smoke_agent_runtime.MUTATION_ACTIVATION_SMOKE_LIVE_BINDING_SOURCE,
        "executor_name": smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
        smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD: (
            smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_GUARDED_LIVE_EXECUTOR
        ),
    }
    assert result["checks"][5]["summary"]["mutation_executor"]["selection_state"] == "guarded_live_executor"
    assert (
        result["checks"][5]["summary"]["mutation_executor"]["actual_runtime_handler"]
        == "index_service.reindex"
    )
    assert result["checks"][5]["summary"]["mutation_executor"]["actual_runtime_handler_invoked"] is True
    assert result["checks"][5]["summary"]["mutation_executor_result"] == {
        "schema_version": "v1.5.reindex_live_adapter_result.v1",
        "collection_key": "all",
        "operation": "rebuild_vector_index",
        "requested_reset": True,
        "requested_compatibility_bundle": False,
        "audit_sequence_id": 12,
        "audit_storage_path": "/tmp/mutation-audit/audit-20260422.jsonl",
        "rollback_mode": "rebuild_from_source_documents",
        "rollback_collection_key": "all",
        "runtime_chunks": 12,
        "runtime_vectors": 34,
        "runtime_scope": "default_runtime_only",
        "runtime_collection": "doc_rag_main",
        "runtime_reindex_scope": "default_runtime_only",
    }


def test_guarded_stage_apply_check_requires_runtime_sidecar():
    guarded_stage = (
        smoke_agent_runtime.mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_GUARDED_LIVE_EXECUTOR
    )
    incomplete_summary = {
        "mutation_executor": {
            "selection_state": "guarded_live_executor",
            "actual_runtime_handler": "index_service.reindex",
            "actual_runtime_handler_invoked": True,
        },
        "mutation_top_level_promotion_router": {
            "success_eligible": False,
        },
    }

    assert smoke_agent_runtime._apply_not_enabled_stage_evidence_ok(incomplete_summary, guarded_stage) is False

    complete_summary = {
        **incomplete_summary,
        "mutation_executor_result": {
            "runtime_chunks": 12,
            "runtime_vectors": 34,
        },
        "mutation_top_level_promotion_router": {
            "success_eligible": True,
        },
    }

    assert smoke_agent_runtime._apply_not_enabled_stage_evidence_ok(complete_summary, guarded_stage) is True


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
