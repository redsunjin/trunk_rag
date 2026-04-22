from __future__ import annotations

from services import (
    actor_policy_service,
    mutation_executor_service,
    tool_apply_service,
    tool_audit_sink_service,
    tool_middleware_service,
    tool_trace_service,
)
from services.tool_registry_service import ToolContext


def _expected_reindex_boundary() -> dict[str, object]:
    return {
        "family": "reindex",
        "classification": "derivative_runtime_state",
        "live_candidate_allowed": True,
        "managed_state_write": False,
        "approval_state_write": False,
        "requires_durable_audit_receipt": True,
        "requires_rollback_plan": False,
        "requires_managed_state_snapshot": False,
        "requires_document_version_binding": False,
        "requires_decision_audit": False,
        "required_preconditions": ["operator_activation", "durable_audit_ready"],
        "blocked_by": [],
        "live_adapter_outline": {
            "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_OUTLINE_SCHEMA_VERSION,
            "status": "outline_only_deferred",
            "target_executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
            "current_executor_name": mutation_executor_service.REINDEX_MUTATION_EXECUTOR_NAME,
            "handoff_from_selection_state": "candidate_stub",
            "execution_mode": "off_by_default",
            "required_inputs": [
                "payload.collection",
                "preview_seed.target.collection_key",
                "apply_envelope.preview_ref",
                "apply_envelope.intent.summary",
                "persisted_audit_record.request_id",
                "audit_sink_receipt.sequence_id",
            ],
            "expected_outputs": [
                "result.reindex_summary",
                "result.audit_receipt_ref",
                "result.rollback_hint",
            ],
            "success_contract": {
                "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION,
                "status": "succeeded",
                "required_fields": [
                    "result.reindex_summary.collection_key",
                    "result.reindex_summary.operation",
                    "result.reindex_summary.source_basis",
                    "result.audit_receipt_ref.sequence_id",
                    "result.rollback_hint.mode",
                ],
                "reindex_summary": {
                    "operation": "rebuild_vector_index",
                    "source_basis": "source_documents_snapshot",
                    "reset_allowed": True,
                    "compatibility_bundle_optional": True,
                },
                "audit_receipt_ref": {
                    "source": "append_only_receipt",
                    "sequence_id_required": True,
                    "storage_path_required": True,
                },
                "rollback_hint": {
                    "mode": "rebuild_from_source_documents",
                    "operator_action_required": True,
                },
            },
            "failure_taxonomy": {
                "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
                "codes": [
                    {
                        "code": "REINDEX_TARGET_MISMATCH",
                        "stage": "contract_validation",
                        "retryable": False,
                    },
                    {
                        "code": "REINDEX_AUDIT_LINKAGE_INVALID",
                        "stage": "audit_linkage",
                        "retryable": False,
                    },
                    {
                        "code": "REINDEX_RUNTIME_EXECUTION_FAILED",
                        "stage": "executor_runtime",
                        "retryable": True,
                    },
                    {
                        "code": "REINDEX_ROLLBACK_HINT_UNAVAILABLE",
                        "stage": "post_execution",
                        "retryable": True,
                    },
                ],
            },
            "opt_in_binding": {
                "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_SCHEMA_VERSION,
                "mode": "explicit_local_only",
                "binding_source": "runtime_injected_executor_binding",
                "binding_owner": "local_operator_or_test_harness",
                "default_executor_name": mutation_executor_service.REINDEX_MUTATION_EXECUTOR_NAME,
                "opt_in_executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_contract_fields": [
                    "binding_kind",
                    "binding_source",
                    "executor_name",
                    mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD,
                ],
                "binding_stage_field": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD,
                "default_binding_stage": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_SELECTION_STUB,
                "concrete_executor_stage": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON,
                "selection_precedence": [
                    "tool_registration_boundary",
                    "activation_guard",
                    "candidate_stub_default",
                    "explicit_live_binding_override",
                ],
                "invalid_binding_behavior": "candidate_stub_fallback",
                "live_selection_state": "live_binding_stub",
                "required_signals": [
                    "activation_requested",
                    "durable_audit_ready",
                    "explicit_live_adapter_binding",
                ],
                "public_surface_allowed": False,
                "shared_with_upload_review": False,
            },
            "executor_injection_protocol": {
                "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_INJECTION_PROTOCOL_SCHEMA_VERSION,
                "mode": "request_scoped_local_only",
                "carrier_chain": [
                    "agent_runtime_request.executor_binding",
                    "tool_context.executor_binding",
                    "mutation_execution_request.executor_binding",
                ],
                "direct_entrypoints": [
                    "agent_runtime_service.run_agent_entry",
                    "tool_middleware_service.invoke_tool_with_middlewares",
                    "mutation_executor_service.build_mutation_execution_request",
                ],
                "payload_channel_allowed": False,
                "binding_owner": "local_runtime_or_test_harness",
                "default_behavior": "absent_binding_keeps_candidate_stub",
                "contract_signal_fields": [
                    "request.executor_binding_present",
                    "request.executor_binding_kind",
                    "request.executor_binding_source",
                    "request.executor_binding_executor_name",
                ],
                "required_guards": [
                    "activation_requested",
                    "durable_audit_ready",
                    "explicit_live_adapter_binding",
                ],
            },
            "opt_in_smoke_harness": {
                "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_SMOKE_HARNESS_SCHEMA_VERSION,
                "mode": "separate_from_default_smoke",
                "default_command": "./.venv/bin/python scripts/smoke_agent_runtime.py",
                "future_command_kind": "explicit_live_adapter_binding_required",
                "prerequisites": [
                    "activation_requested",
                    "durable_audit_ready",
                    "explicit_live_adapter_binding",
                    "local_only_runtime_context",
                ],
                "expected_evidence": [
                    "result.ok=true",
                    "result.mutation_executor.executor_name=reindex_mutation_adapter_live",
                    "result.result.reindex_summary",
                    "result.result.audit_receipt_ref",
                    "result.result.rollback_hint",
                ],
                "isolation": {
                    "shares_default_smoke_suite": False,
                    "upload_review_included": False,
                    "public_surface_allowed": False,
                },
            },
            "rollback_awareness": {
                "mode": "rebuild_from_source_documents",
                "managed_state_rollback_required": False,
                "operator_restore_hint_required": True,
            },
            "test_seams": [
                "noop_fallback_contract",
                "candidate_stub_contract",
                "future_live_adapter_opt_in_smoke",
            ],
            "non_goals": [
                "managed_state_write_rollback",
                "upload_review_execution",
                "public_agent_endpoint",
            ],
        },
    }


def test_tool_middleware_wraps_read_tool_with_request_id_budget_and_audit():
    result = tool_middleware_service.invoke_tool_with_middlewares(
        "read_doc",
        {"collection": "fr", "doc_key": "fr"},
        context=ToolContext(request_id="", actor="internal_agent"),
        allowed_tools=("read_doc",),
        timeout_seconds=12,
    )

    assert result["ok"] is True
    assert result["result"]["origin"] == "seed"
    assert result["middleware"]["request_id"].startswith("tool-")
    assert result["middleware"]["actor"] == "internal_agent"
    assert result["middleware"]["timeout_seconds"] == 12.0
    assert result["middleware"]["allowed_tools"] == ["read_doc"]
    assert result["middleware"]["policy"]["actor_category"] == "internal_read_only"
    assert result["middleware"]["policy"]["mutation_candidate_tools"] == []
    assert "preview" not in result["middleware"]["contracts"]
    assert "preview_seed" not in result["middleware"]["contracts"]
    assert "mutation_executor" not in result["middleware"]["contracts"]
    assert result["middleware"]["contracts"]["persisted_audit"]["request_id"] == result["middleware"]["request_id"]
    assert result["middleware"]["contracts"]["audit_sink"] == {
        "accepted": True,
        "sink_type": "null_append_only",
        "record_schema_version": "v1.5.mutation_audit_record.v1",
        "sequence_id": None,
    }
    assert result["middleware"]["contracts"]["persisted_audit"]["tool"] == {
        "name": "read_doc",
        "side_effect": "read",
    }
    assert [item["middleware"] for item in result["middleware"]["trace"]] == [
        "request_id",
        "timeout_budget",
        "tool_allowlist",
        "mutation_policy_guard",
        "mutation_apply_guard",
        "unsafe_action_guard",
        "audit_log",
    ]
    assert [item["event"] for item in result["middleware"]["audit_log"]] == [
        "tool.invoke.requested",
        "tool.invoke.completed",
    ]
    assert result["execution_trace"]["schema_version"] == tool_trace_service.TRACE_SCHEMA_VERSION
    assert result["execution_trace"]["request_id"] == result["middleware"]["request_id"]
    assert result["execution_trace"]["tool"]["name"] == "read_doc"
    assert result["execution_trace"]["policy"]["actor_category"] == "internal_read_only"
    assert result["execution_trace"]["contracts"]["audit_sink"]["sink_type"] == "null_append_only"
    assert result["execution_trace"]["contracts"]["persisted_audit"]["actor_category"] == "internal_read_only"
    assert result["execution_trace"]["tool"]["result_seed"]["origin"] == "seed"
    assert result["execution_trace"]["outcome"] == {"ok": True, "error": None}


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
    assert result["execution_trace"]["middleware"]["blocked_by"] == "tool_allowlist"
    assert result["execution_trace"]["outcome"]["error"]["code"] == "TOOL_NOT_ALLOWED"


def test_tool_allowlist_defaults_to_actor_policy_when_not_explicitly_provided(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called when actor policy blocks")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares("reindex", {"collection": "all"})

    assert result["ok"] is False
    assert result["error"]["code"] == "TOOL_NOT_ALLOWED"
    assert result["middleware"]["policy"]["actor_category"] == "internal_read_only"
    assert result["middleware"]["policy"]["mutation_candidate_tools"] == []
    assert result["execution_trace"]["middleware"]["blocked_by"] == "tool_allowlist"


def test_mutation_policy_guard_requires_admin_auth_for_candidate_write(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called before auth")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(actor="maintenance", allow_mutation=True),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "ADMIN_AUTH_REQUIRED"
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_policy_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"


def test_mutation_policy_guard_requires_intent_after_admin_auth(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called before mutation intent")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(actor="maintenance", admin_code="admin1234", allow_mutation=True),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_INTENT_REQUIRED"
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_policy_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"


def test_mutation_policy_guard_requires_preview_after_auth_and_intent(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called before preview")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "PREVIEW_REQUIRED"
    assert result["error"]["preview_contract"] == {
        "schema_version": tool_trace_service.PREVIEW_CONTRACT_SCHEMA_VERSION,
        "request_id": result["middleware"]["request_id"],
        "actor_category": "maintenance_mutation",
        "audit_scope": "maintenance",
        "tool": {
            "name": "reindex",
            "side_effect": "write",
        },
        "target": {
            "collection_key": "all",
            "reset": True,
            "include_compatibility_bundle": False,
            "impact_scope": "core_all_only",
        },
        "preview_fields": [
            "collection_key",
            "reset",
            "include_compatibility_bundle",
            "impact_summary",
        ],
        "expected_side_effect": "Reindex all collection contents.",
        "redaction": {
            "audiences": ["internal", "public", "persisted"],
            "raw_content_allowed": False,
            "admin_code_allowed": False,
            "document_body_allowed": False,
        },
    }
    assert result["error"]["preview_seed"] == {
        "schema_version": "v1.5.mutation_preview_seed.v1",
        "contract_schema_version": tool_trace_service.PREVIEW_CONTRACT_SCHEMA_VERSION,
        "request_id": result["middleware"]["request_id"],
        "actor_category": "maintenance_mutation",
        "audit_scope": "maintenance",
        "tool": {
            "name": "reindex",
            "side_effect": "write",
        },
        "target": {
            "collection_key": "all",
            "reset": True,
            "include_compatibility_bundle": False,
            "impact_scope": "core_all_only",
        },
        "preview_fields": [
            "collection_key",
            "reset",
            "include_compatibility_bundle",
            "impact_summary",
        ],
        "preview": {
            "collection_key": "all",
            "reset": True,
            "include_compatibility_bundle": False,
            "impact_summary": "Reset and reindex all collection contents.",
        },
        "expected_side_effect": "Reindex all collection contents.",
        "resolution": {
            "status": "resolved",
        },
        "redaction": {
            "audiences": ["internal", "public", "persisted"],
            "raw_content_allowed": False,
            "admin_code_allowed": False,
            "document_body_allowed": False,
        },
    }
    assert result["error"]["apply_envelope"] == {
        "schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
        "actor_category": "maintenance_mutation",
        "audit_scope": "maintenance",
        "tool": {
            "name": "reindex",
            "side_effect": "write",
        },
        "preview_ref": {
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "tool_name": "reindex",
            "target": {
                "collection_key": "all",
                "reset": True,
                "include_compatibility_bundle": False,
                "impact_scope": "core_all_only",
            },
        },
        "audit_ref": {
            "sink_type": "null_append_only",
            "record_schema_version": "v1.5.mutation_audit_record.v1",
            "accepted": True,
            "sequence_id": None,
        },
        "intent": {
            "summary": "reindex all",
        },
        "apply_control": {
            "execution_enabled": False,
            "required_signals": ["preview_ref", "audit_ref", "intent.summary"],
        },
    }
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_policy_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"
    assert result["execution_trace"]["contracts"]["preview"] == result["error"]["preview_contract"]
    assert result["execution_trace"]["contracts"]["preview_seed"] == result["error"]["preview_seed"]
    assert result["execution_trace"]["contracts"]["apply_envelope"] == result["error"]["apply_envelope"]
    assert result["execution_trace"]["contracts"]["audit_sink"]["sink_type"] == "null_append_only"
    assert result["execution_trace"]["contracts"]["persisted_audit"]["actor_category"] == "maintenance_mutation"


def test_mutation_apply_guard_detects_preview_reference_mismatch(monkeypatch):
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )
    apply_envelope = dict(preview_result["error"]["apply_envelope"])
    apply_envelope["preview_ref"] = {
        **dict(apply_envelope["preview_ref"]),
        "target": {"collection_key": "fr"},
    }

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=apply_envelope,
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "PREVIEW_REFERENCE_MISMATCH"
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_apply_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_apply_guard"


def test_mutation_apply_guard_requires_audit_sink_receipt(monkeypatch):
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )
    apply_envelope = dict(preview_result["error"]["apply_envelope"])
    apply_envelope.pop("audit_ref", None)

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=apply_envelope,
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "AUDIT_SINK_RECEIPT_REQUIRED"
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_apply_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_apply_guard"


def test_mutation_apply_guard_blocks_valid_envelope_until_execution_is_enabled(monkeypatch):
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_APPLY_NOT_ENABLED"
    assert result["error"]["mutation_executor"] == {
        "schema_version": mutation_executor_service.MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": "noop_mutation_executor",
        "binding_kind": "default_noop",
        "tool_name": "reindex",
        "tool_registered": True,
        "activation_requested": False,
        "execution_enabled": False,
        "selection_state": "noop_fallback",
        "selection_reason": "activation_guard_blocked",
        "registered_executor_name": "reindex_mutation_adapter_stub",
        "activation": {
            "surface_scope": "internal_service_only",
            "activation_source": "local_env_flag",
            "ownership": "operator_local_config",
            "env_key": mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
            "requested": False,
            "first_live_tool_scope": "reindex",
            "durable_audit_required": True,
            "durable_audit_ready": False,
            "audit_sink_type": "null_append_only",
            "audit_sequence_id": None,
            "audit_storage_path": None,
            "blocked_by": ["activation_not_requested", "durable_audit_not_ready"],
        },
        "boundary": _expected_reindex_boundary(),
        "request": {
            "request_id": result["middleware"]["request_id"],
            "actor_category": "maintenance_mutation",
            "allow_mutation": True,
            "timeout_seconds": 30.0,
            "apply_schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "audit_record_schema_version": "v1.5.mutation_audit_record.v1",
            "audit_sink_type": "null_append_only",
            "executor_binding_present": False,
            "executor_binding_kind": None,
            "executor_binding_source": None,
            "executor_binding_executor_name": None,
            "executor_binding_stage": None,
        },
    }
    assert result["middleware"]["trace"][-1]["middleware"] == "mutation_apply_guard"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_apply_guard"
    assert result["execution_trace"]["contracts"]["mutation_executor"] == result["error"]["mutation_executor"]


def test_mutation_apply_guard_exposes_reindex_candidate_stub_when_activation_and_durable_audit_are_ready(
    monkeypatch,
    tmp_path,
):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("direct reindex tool handler must not be called during apply dry-run")

    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)
    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY, str(tmp_path / "mutation_audit"))

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_APPLY_NOT_ENABLED"
    assert result["error"]["mutation_executor"]["executor_name"] == "reindex_mutation_adapter_stub"
    assert result["error"]["mutation_executor"]["selection_state"] == "candidate_stub"
    assert result["error"]["mutation_executor"]["selection_reason"] == "activation_guard_satisfied"
    assert result["error"]["mutation_executor"]["activation_requested"] is True
    activation = result["error"]["mutation_executor"]["activation"]
    assert activation["surface_scope"] == "internal_service_only"
    assert activation["activation_source"] == "local_env_flag"
    assert activation["ownership"] == "operator_local_config"
    assert activation["env_key"] == mutation_executor_service.MUTATION_EXECUTION_ENV_KEY
    assert activation["requested"] is True
    assert activation["first_live_tool_scope"] == "reindex"
    assert activation["durable_audit_required"] is True
    assert activation["durable_audit_ready"] is True
    assert activation["audit_sink_type"] == "local_file_append_only"
    assert activation["audit_sequence_id"] == 2
    assert str(activation["audit_storage_path"]).startswith(str(tmp_path / "mutation_audit" / "audit-"))
    assert str(activation["audit_storage_path"]).endswith(".jsonl")
    assert activation["blocked_by"] == []
    boundary = result["error"]["mutation_executor"]["boundary"]
    assert boundary == _expected_reindex_boundary()
    assert result["error"]["mutation_executor"]["delegate_executor_name"] == "noop_mutation_executor"
    assert result["execution_trace"]["contracts"]["mutation_executor"] == result["error"]["mutation_executor"]
    router_dry_run = result["error"]["mutation_apply_router_dry_run"]
    assert router_dry_run["schema_version"] == (
        mutation_executor_service.REINDEX_MUTATION_APPLY_ROUTER_DRY_RUN_SCHEMA_VERSION
    )
    assert router_dry_run["apply_guard"] == {
        "validated_apply_envelope": True,
        "blocked_error_code": "MUTATION_APPLY_NOT_ENABLED",
        "blocked_by": "mutation_apply_guard",
        "blocks_before_tool_handler": True,
    }
    assert router_dry_run["router_handoff"] == {
        "route_location": "mutation_apply_guard_pre_side_effect_router",
        "request_builder": "tool_middleware_service._build_mutation_execution_request",
        "router": "mutation_executor_service.execute_mutation_request",
        "dry_run_only": True,
        "direct_tool_handler": "tool_registry_service._tool_reindex",
        "actual_runtime_handler": "index_service.reindex",
        "direct_tool_handler_invoked": False,
        "actual_runtime_handler_invoked": False,
    }
    assert router_dry_run["executor_evidence"]["executor_name"] == "reindex_mutation_adapter_stub"
    assert router_dry_run["executor_evidence"]["selection_state"] == "candidate_stub"
    assert router_dry_run["promotion_policy"]["actual_side_effect_enabled"] is False
    assert result["execution_trace"]["contracts"]["mutation_apply_router_dry_run"] == router_dry_run


def test_mutation_apply_guard_forwards_executor_binding_into_mutation_executor_contract(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY, str(tmp_path / "mutation_audit"))

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )

    binding = {
        "binding_kind": "explicit_live_adapter",
        "binding_source": "test_harness",
        "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
    }
    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            executor_binding=binding,
            allow_mutation=True,
        ),
    )

    mutation_executor = result["error"]["mutation_executor"]
    request_contract = mutation_executor["request"]
    assert mutation_executor["executor_name"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    assert mutation_executor["binding_kind"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND
    assert mutation_executor["selection_state"] == "live_binding_stub"
    assert mutation_executor["selection_reason"] == "explicit_live_binding_requested"
    assert request_contract["executor_binding_present"] is True
    assert request_contract["executor_binding_kind"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND
    assert request_contract["executor_binding_source"] == "test_harness"
    assert request_contract["executor_binding_executor_name"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    assert request_contract["executor_binding_stage"] is None


def test_mutation_apply_guard_exposes_live_result_skeleton_sidecar_when_binding_stage_requests_it(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY, str(tmp_path / "mutation_audit"))

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all", "include_compatibility_bundle": True},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
        ),
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all", "include_compatibility_bundle": True},
        context=ToolContext(
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            executor_binding={
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_source": "test_harness",
                "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD: mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON,
            },
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_APPLY_NOT_ENABLED"
    mutation_executor = result["error"]["mutation_executor"]
    assert mutation_executor["selection_state"] == "live_result_skeleton"
    assert mutation_executor["execution_enabled"] is True
    mutation_executor_result = result["error"]["mutation_executor_result"]
    assert mutation_executor_result["schema_version"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION
    assert mutation_executor_result["reindex_summary"]["collection_key"] == "all"
    assert mutation_executor_result["reindex_summary"]["requested_compatibility_bundle"] is True
    assert result["execution_trace"]["contracts"]["mutation_executor_result"] == mutation_executor_result
    mutation_success_promotion = result["error"]["mutation_success_promotion"]
    assert mutation_success_promotion["schema_version"] == (
        mutation_executor_service.REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_SCHEMA_VERSION
    )
    assert mutation_success_promotion["current_surface"] == {
        "kind": "blocked_success_sidecar",
        "top_level_ok": False,
        "top_level_error_code": "MUTATION_APPLY_NOT_ENABLED",
        "result_location": "error.mutation_executor_result",
        "contract_location": "execution_trace.contracts.mutation_executor_result",
        "blocked_by": "mutation_apply_guard",
    }
    assert mutation_success_promotion["future_success_surface"]["result_location"] == "result"
    assert mutation_success_promotion["future_success_surface"]["promoted_fields"] == [
        "reindex_summary",
        "audit_receipt_ref",
        "rollback_hint",
    ]
    assert mutation_success_promotion["promotion_gate"]["actual_side_effect_enabled"] is False
    assert result["execution_trace"]["contracts"]["mutation_success_promotion"] == mutation_success_promotion
    promotion_router = result["error"]["mutation_top_level_promotion_router"]
    assert promotion_router["schema_version"] == (
        mutation_executor_service.REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_ROUTER_SCHEMA_VERSION
    )
    assert promotion_router["router_state"] == "draft_ready_not_enabled"
    assert promotion_router["current_runtime_surface"]["top_level_error_code"] == "MUTATION_APPLY_NOT_ENABLED"
    assert promotion_router["success_route"]["eligible"] is True
    assert promotion_router["success_route"]["target_result_location"] == "result"
    assert promotion_router["success_result_preview"] == mutation_executor_result
    assert promotion_router["failure_route"]["target_error_location"] == "error"
    assert promotion_router["failure_route"]["supported_codes"] == [
        mutation_executor_service.REINDEX_ERROR_TARGET_MISMATCH,
        mutation_executor_service.REINDEX_ERROR_AUDIT_LINKAGE_INVALID,
        mutation_executor_service.REINDEX_ERROR_RUNTIME_EXECUTION_FAILED,
        mutation_executor_service.REINDEX_ERROR_ROLLBACK_HINT_UNAVAILABLE,
    ]
    assert promotion_router["promotion_gate"]["top_level_promotion_enabled"] is False
    assert promotion_router["promotion_gate"]["actual_side_effect_enabled"] is False
    assert result["execution_trace"]["contracts"]["mutation_top_level_promotion_router"] == promotion_router


def test_mutation_apply_guard_keeps_upload_review_in_boundary_noop_even_when_activation_and_durable_audit_are_ready(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(tool_middleware_service.runtime_service, "verify_admin_code", lambda code: None)
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY, str(tmp_path / "mutation_audit"))
    monkeypatch.setattr(
        tool_middleware_service.tool_preview_service.upload_service,
        "get_upload_request_view",
        lambda request_id: {
            "id": request_id,
            "status": "pending",
            "request_type": "update",
            "doc_key": "fr-summary",
        },
    )

    preview_result = tool_middleware_service.invoke_tool_with_middlewares(
        "approve_upload_request",
        {"request_id": "upload-42"},
        context=ToolContext(
            actor="admin",
            admin_code="admin1234",
            mutation_intent="approve upload-42",
            allow_mutation=True,
        ),
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "approve_upload_request",
        {"request_id": "upload-42"},
        context=ToolContext(
            actor="admin",
            admin_code="admin1234",
            mutation_intent="approve upload-42",
            apply_envelope=preview_result["error"]["apply_envelope"],
            allow_mutation=True,
        ),
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_APPLY_NOT_ENABLED"
    assert result["error"]["mutation_executor"]["executor_name"] == "noop_mutation_executor"
    assert result["error"]["mutation_executor"]["tool_name"] == "approve_upload_request"
    assert result["error"]["mutation_executor"]["tool_registered"] is False
    assert result["error"]["mutation_executor"]["selection_state"] == "boundary_noop"
    assert result["error"]["mutation_executor"]["selection_reason"] == "upload_review_scope_deferred"
    activation = result["error"]["mutation_executor"]["activation"]
    assert activation["requested"] is True
    assert activation["durable_audit_required"] is False
    assert activation["audit_sink_type"] == "local_file_append_only"
    assert activation["audit_sequence_id"] == 2
    assert str(activation["audit_storage_path"]).startswith(str(tmp_path / "mutation_audit" / "audit-"))
    assert str(activation["audit_storage_path"]).endswith(".jsonl")
    assert activation["blocked_by"] == []
    boundary = result["error"]["mutation_executor"]["boundary"]
    assert boundary == {
        "family": "upload_review",
        "classification": "managed_doc_activation",
        "live_candidate_allowed": False,
        "managed_state_write": True,
        "approval_state_write": True,
        "requires_durable_audit_receipt": True,
        "requires_rollback_plan": True,
        "requires_managed_state_snapshot": True,
        "requires_document_version_binding": True,
        "requires_decision_audit": True,
        "required_preconditions": [
            "separate_upload_review_go_no_go",
            "decision_audit_contract",
            "managed_state_snapshot",
            "document_version_binding",
            "rollback_plan",
        ],
        "blocked_by": [
            "upload_review_scope_deferred",
            "managed_state_rollback_not_ready",
            "document_version_binding_not_reviewed",
        ],
    }
    assert result["execution_trace"]["contracts"]["mutation_executor"] == result["error"]["mutation_executor"]


def test_unsafe_action_guard_blocks_write_without_mutation_context(monkeypatch):
    def fail_if_invoked(*args, **kwargs):
        raise AssertionError("write adapter must not be called without mutation context")

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fail_if_invoked)
    policy_decision = actor_policy_service.ActorPolicyDecision(
        actor="maintenance",
        actor_category="maintenance_mutation",
        read_allowed_tools=("health_check",),
        mutation_candidate_tools=("reindex",),
        effective_allowed_tools=("reindex",),
        requires_admin_auth=False,
        requires_mutation_intent=False,
        requires_preview_before_apply=False,
        audit_scope="maintenance",
        source_schema_version="v1.5.actor_policy_source.v1",
        source_path="config/actor_policy_manifest.json",
        used_fallback=False,
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(actor="maintenance"),
        policy_decision=policy_decision,
    )

    assert result["ok"] is False
    assert result["error"]["code"] == "MUTATION_NOT_ALLOWED"
    assert result["middleware"]["trace"][-1]["middleware"] == "unsafe_action_guard"
    assert result["middleware"]["trace"][-1]["status"] == "blocked"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "unsafe_action_guard"


def test_mutation_context_and_timeout_budget_are_passed_to_registry(monkeypatch):
    captured = {}

    def fake_invoke_tool(name, payload, *, context=None):
        captured["name"] = name
        captured["payload"] = payload
        captured["context"] = context
        return {"tool": name, "ok": True, "result": {"status": "queued"}, "error": None}

    monkeypatch.setattr(tool_middleware_service.tool_registry_service, "invoke_tool", fake_invoke_tool)
    policy_decision = actor_policy_service.ActorPolicyDecision(
        actor="maintenance",
        actor_category="maintenance_mutation",
        read_allowed_tools=("health_check", "list_collections"),
        mutation_candidate_tools=("reindex",),
        effective_allowed_tools=("health_check", "list_collections", "reindex"),
        requires_admin_auth=False,
        requires_mutation_intent=False,
        requires_preview_before_apply=False,
        audit_scope="maintenance",
        source_schema_version="v1.5.actor_policy_source.v1",
        source_path="config/actor_policy_manifest.json",
        used_fallback=False,
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "reindex",
        {"collection": "all"},
        context=ToolContext(request_id="req-1", actor="maintenance", allow_mutation=True),
        policy_decision=policy_decision,
        timeout_seconds=7,
    )

    assert result["ok"] is True
    assert captured["name"] == "reindex"
    assert captured["payload"] == {"collection": "all"}
    assert captured["context"].request_id == "req-1"
    assert captured["context"].actor == "maintenance"
    assert captured["context"].allow_mutation is True
    assert captured["context"].timeout_seconds == 7.0
    assert result["middleware"]["policy"]["actor_category"] == "maintenance_mutation"
    assert result["middleware"]["policy"]["mutation_candidate_tools"] == ["reindex"]
    assert result["middleware"]["audit_log"][-1]["event"] == "tool.invoke.completed"


def test_execution_trace_includes_search_docs_routing_seed(monkeypatch):
    def fake_build_collection_context(*, question, collection_keys, trace, budget):
        trace.update({"collections": list(collection_keys), "sources": [{"source": "fr.md"}]})
        return "context"

    monkeypatch.setattr(
        tool_middleware_service.tool_registry_service.query_service,
        "build_collection_context",
        fake_build_collection_context,
    )

    result = tool_middleware_service.invoke_tool_with_middlewares(
        "search_docs",
        {"query": "프랑스 과학 인재 양성을 요약해줘.", "query_profile": "sample_pack"},
        context=ToolContext(request_id="req-search"),
        allowed_tools=("search_docs",),
        timeout_seconds=9,
    )

    assert result["ok"] is True
    assert result["execution_trace"]["routing"]["route_reason"] == "compatibility_keyword"
    assert result["execution_trace"]["routing"]["collections"] == ["fr"]
    assert result["execution_trace"]["routing"]["query_profile"] == "sample_pack"
    assert result["execution_trace"]["tool"]["result_seed"]["source_count"] == 1


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
