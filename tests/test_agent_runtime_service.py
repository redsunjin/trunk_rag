from __future__ import annotations

from services import agent_runtime_service, mutation_executor_service, tool_apply_service, tool_audit_sink_service


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


def test_agent_entry_defaults_single_input_to_search_docs(monkeypatch):
    captured = {}

    def fake_invoke_tool_with_middlewares(
        name,
        payload,
        *,
        context=None,
        allowed_tools=None,
        policy_decision=None,
        timeout_seconds=None,
    ):
        captured["name"] = name
        captured["payload"] = payload
        captured["context"] = context
        captured["allowed_tools"] = allowed_tools
        captured["policy_decision"] = policy_decision
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
    assert captured["policy_decision"].actor_category == "internal_read_only"
    assert captured["allowed_tools"] == (
        "search_docs",
        "read_doc",
        "list_collections",
        "health_check",
    )
    assert result["entry"]["actor_category"] == "internal_read_only"
    assert result["entry"]["mutation_candidate_tools"] == []
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

    def fake_invoke_tool_with_middlewares(
        name,
        payload,
        *,
        context=None,
        allowed_tools=None,
        policy_decision=None,
        timeout_seconds=None,
    ):
        captured["name"] = name
        captured["payload"] = payload
        captured["allowed_tools"] = allowed_tools
        captured["policy_decision"] = policy_decision
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
    assert captured["policy_decision"].actor_category == "internal_read_only"
    assert "read_doc" in captured["allowed_tools"]


def test_agent_entry_forwards_executor_binding_into_tool_context(monkeypatch):
    captured = {}

    def fake_invoke_tool_with_middlewares(
        name,
        payload,
        *,
        context=None,
        allowed_tools=None,
        policy_decision=None,
        timeout_seconds=None,
    ):
        captured["context"] = context
        return {
            "tool": name,
            "ok": True,
            "result": {"status": "queued"},
            "error": None,
            "execution_trace": {"request_id": "agent-binding-1", "outcome": {"ok": True, "error": None}},
        }

    monkeypatch.setattr(agent_runtime_service.tool_middleware_service, "invoke_tool_with_middlewares", fake_invoke_tool_with_middlewares)

    binding = {
        "binding_kind": "explicit_live_adapter",
        "binding_source": "test_harness",
        "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
    }
    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed reindex plan.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            request_id="agent-binding-1",
            executor_binding=binding,
        )
    )

    assert captured["context"].executor_binding == binding
    assert result["entry"]["executor_binding_present"] is True


def test_agent_entry_uses_actor_policy_fallback_for_unknown_actor():
    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="문서 상태를 보여줘.",
            tool_name="read_doc",
            tool_payload={"collection": "fr", "doc_key": "fr"},
            actor="guest-bot",
            request_id="guest-1",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["actor_category"] == "unknown_read_only"
    assert result["entry"]["allowed_tools"] == ["health_check"]
    assert result["entry"]["policy_flags"]["used_fallback"] is True
    assert result["error"]["code"] == "TOOL_NOT_ALLOWED"


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
    assert result["entry"]["actor_category"] == "internal_read_only"
    assert result["entry"]["mutation_candidate_tools"] == []
    assert result["execution_trace"]["middleware"]["blocked_by"] == "tool_allowlist"


def test_agent_entry_requires_admin_auth_for_mutation_candidate(monkeypatch):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            allow_mutation=True,
            request_id="maintenance-auth-1",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["actor_category"] == "maintenance_mutation"
    assert result["entry"]["allowed_tools"] == ["health_check", "list_collections", "reindex"]
    assert result["error"]["code"] == "ADMIN_AUTH_REQUIRED"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"


def test_agent_entry_requires_mutation_intent_after_admin_auth(monkeypatch):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            allow_mutation=True,
            request_id="maintenance-intent-1",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["admin_code_present"] is True
    assert result["entry"]["mutation_intent_present"] is False
    assert result["error"]["code"] == "MUTATION_INTENT_REQUIRED"
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"


def test_agent_entry_requires_preview_after_admin_auth_and_intent(monkeypatch):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
            request_id="maintenance-preview-1",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["admin_code_present"] is True
    assert result["entry"]["mutation_intent_present"] is True
    assert result["entry"]["apply_envelope_present"] is False
    assert result["error"]["code"] == "PREVIEW_REQUIRED"
    assert result["error"]["preview_contract"] == {
        "schema_version": "v1.5.mutation_preview_contract.v1",
        "request_id": "maintenance-preview-1",
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
        "contract_schema_version": "v1.5.mutation_preview_contract.v1",
        "request_id": "maintenance-preview-1",
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
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_policy_guard"
    assert result["execution_trace"]["contracts"]["preview"] == result["error"]["preview_contract"]
    assert result["execution_trace"]["contracts"]["preview_seed"] == result["error"]["preview_seed"]
    assert result["execution_trace"]["contracts"]["apply_envelope"] == result["error"]["apply_envelope"]
    assert result["execution_trace"]["contracts"]["audit_sink"]["sink_type"] == "null_append_only"
    assert result["execution_trace"]["contracts"]["persisted_audit"]["request_id"] == "maintenance-preview-1"


def test_agent_entry_blocks_preview_confirmed_apply_until_execution_is_enabled(monkeypatch):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )

    preview_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
            request_id="maintenance-preview-2",
        )
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed reindex plan.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            allow_mutation=True,
            request_id="maintenance-apply-1",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["admin_code_present"] is True
    assert result["entry"]["mutation_intent_present"] is True
    assert result["entry"]["apply_envelope_present"] is True
    assert result["error"]["code"] == "MUTATION_APPLY_NOT_ENABLED"
    assert result["error"]["submitted_apply_envelope"] == preview_result["error"]["apply_envelope"]
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
            "request_id": "maintenance-apply-1",
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
    assert result["execution_trace"]["middleware"]["blocked_by"] == "mutation_apply_guard"
    assert result["execution_trace"]["contracts"]["apply_envelope"] == result["error"]["apply_envelope"]
    assert result["execution_trace"]["contracts"]["mutation_executor"] == result["error"]["mutation_executor"]


def test_agent_entry_exposes_reindex_candidate_stub_when_activation_and_durable_audit_are_ready(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(
        tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
        str(tmp_path / "mutation_audit"),
    )

    preview_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
            request_id="maintenance-preview-3",
        )
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed reindex plan.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            allow_mutation=True,
            request_id="maintenance-apply-2",
        )
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
    assert router_dry_run["router_handoff"]["route_location"] == "mutation_apply_guard_pre_side_effect_router"
    assert router_dry_run["router_handoff"]["direct_tool_handler_invoked"] is False
    assert router_dry_run["router_handoff"]["actual_runtime_handler_invoked"] is False
    assert router_dry_run["executor_evidence"]["selection_state"] == "candidate_stub"
    assert result["execution_trace"]["contracts"]["mutation_apply_router_dry_run"] == router_dry_run


def test_agent_entry_selects_live_binding_stub_when_executor_binding_is_injected(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(
        tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
        str(tmp_path / "mutation_audit"),
    )

    preview_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
            request_id="maintenance-preview-live-1",
        )
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed reindex plan.",
            tool_name="reindex",
            tool_payload={"collection": "all"},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            apply_envelope=preview_result["error"]["apply_envelope"],
            executor_binding={
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_source": "test_harness",
                "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
            },
            allow_mutation=True,
            request_id="maintenance-apply-live-1",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["executor_binding_present"] is True
    mutation_executor = result["error"]["mutation_executor"]
    assert mutation_executor["executor_name"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    assert mutation_executor["binding_kind"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND
    assert mutation_executor["selection_state"] == "live_binding_stub"
    assert mutation_executor["selection_reason"] == "explicit_live_binding_requested"
    assert mutation_executor["request"]["executor_binding_present"] is True
    assert mutation_executor["request"]["executor_binding_source"] == "test_harness"
    assert mutation_executor["request"]["executor_binding_stage"] is None


def test_agent_entry_exposes_live_result_skeleton_sidecar_when_binding_stage_requests_it(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(
        tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
        str(tmp_path / "mutation_audit"),
    )

    preview_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Reindex the core collection.",
            tool_name="reindex",
            tool_payload={"collection": "all", "include_compatibility_bundle": True},
            actor="maintenance",
            admin_code="admin1234",
            mutation_intent="reindex all",
            allow_mutation=True,
            request_id="maintenance-preview-live-2",
        )
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed reindex plan.",
            tool_name="reindex",
            tool_payload={"collection": "all", "include_compatibility_bundle": True},
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
            request_id="maintenance-apply-live-2",
        )
    )

    assert result["ok"] is False
    assert result["entry"]["executor_binding_present"] is True
    assert result["error"]["code"] == "MUTATION_APPLY_NOT_ENABLED"
    mutation_executor = result["error"]["mutation_executor"]
    assert mutation_executor["selection_state"] == "live_result_skeleton"
    assert mutation_executor["execution_enabled"] is True
    mutation_executor_result = result["error"]["mutation_executor_result"]
    assert mutation_executor_result["schema_version"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION
    assert mutation_executor_result["rollback_hint"]["collection_key"] == "all"
    assert result["execution_trace"]["contracts"]["mutation_executor_result"] == mutation_executor_result
    mutation_success_promotion = result["error"]["mutation_success_promotion"]
    assert mutation_success_promotion["schema_version"] == (
        mutation_executor_service.REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_SCHEMA_VERSION
    )
    assert mutation_success_promotion["promotion_state"] == "draft_ready_not_enabled"
    assert mutation_success_promotion["current_surface"]["result_location"] == "error.mutation_executor_result"
    assert mutation_success_promotion["future_success_surface"]["result_location"] == "result"
    assert mutation_success_promotion["future_success_surface"]["top_level_ok"] is True
    assert mutation_success_promotion["promotion_gate"]["default_behavior"] == "remain_blocked_success_sidecar"
    assert result["execution_trace"]["contracts"]["mutation_success_promotion"] == mutation_success_promotion
    promotion_router = result["error"]["mutation_top_level_promotion_router"]
    assert promotion_router["schema_version"] == (
        mutation_executor_service.REINDEX_LIVE_ADAPTER_TOP_LEVEL_PROMOTION_ROUTER_SCHEMA_VERSION
    )
    assert promotion_router["success_route"]["eligible"] is True
    assert promotion_router["success_route"]["target_top_level_ok"] is True
    assert promotion_router["success_result_preview"] == mutation_executor_result
    assert promotion_router["failure_route"]["supported_codes"] == [
        mutation_executor_service.REINDEX_ERROR_TARGET_MISMATCH,
        mutation_executor_service.REINDEX_ERROR_AUDIT_LINKAGE_INVALID,
        mutation_executor_service.REINDEX_ERROR_RUNTIME_EXECUTION_FAILED,
        mutation_executor_service.REINDEX_ERROR_ROLLBACK_HINT_UNAVAILABLE,
    ]
    assert promotion_router["promotion_gate"]["top_level_promotion_enabled"] is False
    assert result["execution_trace"]["contracts"]["mutation_top_level_promotion_router"] == promotion_router


def test_agent_entry_keeps_upload_review_in_boundary_noop_even_when_activation_and_durable_audit_are_ready(
    monkeypatch,
    tmp_path,
):
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.runtime_service,
        "verify_admin_code",
        lambda code: None,
    )
    monkeypatch.setattr(
        agent_runtime_service.tool_middleware_service.tool_preview_service.upload_service,
        "get_upload_request_view",
        lambda request_id: {
            "id": request_id,
            "status": "pending",
            "request_type": "update",
            "doc_key": "fr-summary",
        },
    )
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(
        tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY,
        str(tmp_path / "mutation_audit"),
    )

    preview_result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Approve the pending upload request.",
            tool_name="approve_upload_request",
            tool_payload={"request_id": "upload-42"},
            actor="admin",
            admin_code="admin1234",
            mutation_intent="approve upload-42",
            allow_mutation=True,
            request_id="admin-preview-1",
        )
    )

    result = agent_runtime_service.run_agent_entry(
        agent_runtime_service.AgentRuntimeRequest(
            input="Apply the confirmed upload review decision.",
            tool_name="approve_upload_request",
            tool_payload={"request_id": "upload-42"},
            actor="admin",
            admin_code="admin1234",
            mutation_intent="approve upload-42",
            apply_envelope=preview_result["error"]["apply_envelope"],
            allow_mutation=True,
            request_id="admin-apply-1",
        )
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
