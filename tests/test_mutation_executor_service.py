from __future__ import annotations

from services import mutation_executor_service, tool_apply_service


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


def _sample_request(
    tool_name: str = "reindex",
    *,
    payload: dict[str, object] | None = None,
    audit_sink_receipt: dict[str, object] | None = None,
    executor_binding: dict[str, object] | None = None,
    actor: str = "maintenance",
    actor_category: str = "maintenance_mutation",
) -> mutation_executor_service.MutationExecutionRequest:
    apply_envelope = {
        "schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
        "preview_ref": {
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "tool_name": tool_name,
            "target": {"collection_key": "all"},
        },
    }
    preview_seed = {
        "schema_version": "v1.5.mutation_preview_seed.v1",
        "tool": {
            "name": tool_name,
            "side_effect": "write",
        },
    }
    persisted_audit_record = {
        "schema_version": "v1.5.mutation_audit_record.v1",
    }
    resolved_audit_sink_receipt = audit_sink_receipt or {
        "sink_type": "null_append_only",
    }
    request = mutation_executor_service.build_mutation_execution_request(
        request_id="req-exec-1",
        tool_name=tool_name,
        payload=payload or {"collection": "all"},
        apply_envelope=apply_envelope,
        preview_seed=preview_seed,
        persisted_audit_record=persisted_audit_record,
        audit_sink_receipt=resolved_audit_sink_receipt,
        actor=actor,
        actor_category=actor_category,
        allow_mutation=True,
        timeout_seconds=7,
        executor_binding=executor_binding,
    )
    assert request is not None
    return request


def test_build_mutation_execution_request_preserves_optional_executor_binding():
    binding = {
        "binding_kind": "explicit_live_adapter",
        "binding_source": "test_harness",
        "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
    }

    request = _sample_request("reindex", executor_binding=binding)

    assert request.executor_binding == binding


def test_execute_mutation_request_uses_noop_fallback_for_reindex_when_activation_guard_is_not_satisfied(monkeypatch):
    monkeypatch.delenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, raising=False)

    result = mutation_executor_service.execute_mutation_request(_sample_request("reindex"))

    assert result["ok"] is False
    assert result["error"] == {
        "code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
        "message": "Mutation apply handshake validated, but execution is not enabled yet.",
    }
    assert result["executor"] == {
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
            "request_id": "req-exec-1",
            "actor_category": "maintenance_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
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


def test_execute_mutation_request_keeps_reindex_in_noop_fallback_without_durable_audit_backend(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(_sample_request("reindex"))

    assert result["ok"] is False
    assert result["error"]["code"] == tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED
    assert result["executor"] == {
        "schema_version": mutation_executor_service.MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": "noop_mutation_executor",
        "binding_kind": "default_noop",
        "tool_name": "reindex",
        "tool_registered": True,
        "activation_requested": True,
        "execution_enabled": False,
        "selection_state": "noop_fallback",
        "selection_reason": "activation_guard_blocked",
        "registered_executor_name": "reindex_mutation_adapter_stub",
        "activation": {
            "surface_scope": "internal_service_only",
            "activation_source": "local_env_flag",
            "ownership": "operator_local_config",
            "env_key": mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
            "requested": True,
            "first_live_tool_scope": "reindex",
            "durable_audit_required": True,
            "durable_audit_ready": False,
            "audit_sink_type": "null_append_only",
            "audit_sequence_id": None,
            "audit_storage_path": None,
            "blocked_by": ["durable_audit_not_ready"],
        },
        "boundary": _expected_reindex_boundary(),
        "request": {
            "request_id": "req-exec-1",
            "actor_category": "maintenance_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
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


def test_execute_mutation_request_selects_reindex_candidate_stub_when_activation_guard_is_satisfied(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reindex",
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
        )
    )

    assert result["ok"] is False
    assert result["error"] == {
        "code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
        "message": "Mutation apply handshake validated, but execution is not enabled yet.",
    }
    assert result["executor"] == {
        "schema_version": mutation_executor_service.MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": "reindex_mutation_adapter_stub",
        "binding_kind": "tool_adapter_stub",
        "tool_name": "reindex",
        "tool_registered": True,
        "activation_requested": True,
        "execution_enabled": False,
        "selection_state": "candidate_stub",
        "selection_reason": "activation_guard_satisfied",
        "activation": {
            "surface_scope": "internal_service_only",
            "activation_source": "local_env_flag",
            "ownership": "operator_local_config",
            "env_key": mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
            "requested": True,
            "first_live_tool_scope": "reindex",
            "durable_audit_required": True,
            "durable_audit_ready": True,
            "audit_sink_type": "local_file_append_only",
            "audit_sequence_id": 11,
            "audit_storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            "blocked_by": [],
        },
        "boundary": _expected_reindex_boundary(),
        "delegate_executor_name": "noop_mutation_executor",
        "request": {
            "request_id": "req-exec-1",
            "actor_category": "maintenance_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
            "apply_schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "audit_record_schema_version": "v1.5.mutation_audit_record.v1",
            "audit_sink_type": "local_file_append_only",
            "executor_binding_present": False,
            "executor_binding_kind": None,
            "executor_binding_source": None,
            "executor_binding_executor_name": None,
            "executor_binding_stage": None,
        },
    }


def test_execute_mutation_request_selects_live_binding_stub_when_explicit_binding_is_injected(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reindex",
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
            executor_binding={
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_source": "test_harness",
                "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
            },
        )
    )

    assert result["ok"] is False
    assert result["executor"]["executor_name"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    assert result["executor"]["binding_kind"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND
    assert result["executor"]["selection_state"] == "live_binding_stub"
    assert result["executor"]["selection_reason"] == "explicit_live_binding_requested"
    assert result["executor"]["registered_executor_name"] == mutation_executor_service.REINDEX_MUTATION_EXECUTOR_NAME
    assert result["executor"]["delegate_executor_name"] == mutation_executor_service.NOOP_MUTATION_EXECUTOR_NAME
    assert result["executor"]["request"]["executor_binding_present"] is True
    assert result["executor"]["request"]["executor_binding_source"] == "test_harness"
    assert result["executor"]["request"]["executor_binding_stage"] is None


def test_execute_mutation_request_selects_live_result_skeleton_when_binding_stage_requests_it(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reindex",
            payload={"collection": "all", "reset": True, "include_compatibility_bundle": True},
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
            executor_binding={
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_source": "test_harness",
                "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD: mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON,
            },
        )
    )

    assert result["ok"] is True
    assert result["error"] is None
    assert result["executor"]["executor_name"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME
    assert result["executor"]["selection_state"] == "live_result_skeleton"
    assert result["executor"]["selection_reason"] == "explicit_live_result_contract_requested"
    assert result["executor"]["execution_enabled"] is True
    assert result["executor"]["request"]["executor_binding_stage"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON
    assert result["result"] == {
        "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION,
        "reindex_summary": {
            "collection_key": "all",
            "operation": "rebuild_vector_index",
            "source_basis": "source_documents_snapshot",
            "requested_reset": True,
            "requested_compatibility_bundle": True,
        },
        "audit_receipt_ref": {
            "source": "append_only_receipt",
            "sequence_id": 11,
            "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
        },
        "rollback_hint": {
            "mode": "rebuild_from_source_documents",
            "operator_action_required": True,
            "collection_key": "all",
        },
    }


def test_build_reindex_live_success_promotion_contract_maps_sidecar_to_future_surface(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reindex",
            payload={"collection": "all", "reset": True, "include_compatibility_bundle": True},
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
            executor_binding={
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_source": "test_harness",
                "executor_name": mutation_executor_service.REINDEX_LIVE_ADAPTER_EXECUTOR_NAME,
                mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_FIELD: mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_STAGE_CONCRETE_SKELETON,
            },
        )
    )

    promotion = mutation_executor_service.build_reindex_live_success_promotion_contract(
        executor_contract=result["executor"],
        executor_result=result["result"],
    )

    assert promotion == {
        "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_SUCCESS_PROMOTION_SCHEMA_VERSION,
        "tool_name": "reindex",
        "promotion_state": "draft_ready_not_enabled",
        "selection_state": "live_result_skeleton",
        "selection_reason": "explicit_live_result_contract_requested",
        "current_surface": {
            "kind": "blocked_success_sidecar",
            "top_level_ok": False,
            "top_level_error_code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
            "result_location": "error.mutation_executor_result",
            "contract_location": "execution_trace.contracts.mutation_executor_result",
            "blocked_by": "mutation_apply_guard",
        },
        "future_success_surface": {
            "kind": "top_level_apply_success",
            "top_level_ok": True,
            "top_level_error": None,
            "result_location": "result",
            "result_schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_RESULT_SCHEMA_VERSION,
            "promoted_fields": [
                "reindex_summary",
                "audit_receipt_ref",
                "rollback_hint",
            ],
            "retained_contracts": [
                "mutation_executor",
                "mutation_executor_result",
                "mutation_success_promotion",
            ],
        },
        "promotion_gate": {
            "default_behavior": "remain_blocked_success_sidecar",
            "actual_side_effect_enabled": False,
            "requires": [
                "mutation_apply_guard_execution_enabled",
                "executor_result_ok",
                "live_result_skeleton",
                "durable_audit_ready",
                "explicit_live_adapter_binding",
            ],
        },
        "result_summary": {
            "collection_key": "all",
            "operation": "rebuild_vector_index",
            "requested_reset": True,
            "requested_compatibility_bundle": True,
            "audit_sequence_id": 11,
            "rollback_mode": "rebuild_from_source_documents",
        },
    }


def test_list_reindex_live_failure_contracts_maps_all_taxonomy_codes_to_future_failure_surface():
    contracts = mutation_executor_service.list_reindex_live_failure_contracts()

    assert [contract["code"] for contract in contracts] == [
        mutation_executor_service.REINDEX_ERROR_TARGET_MISMATCH,
        mutation_executor_service.REINDEX_ERROR_AUDIT_LINKAGE_INVALID,
        mutation_executor_service.REINDEX_ERROR_RUNTIME_EXECUTION_FAILED,
        mutation_executor_service.REINDEX_ERROR_ROLLBACK_HINT_UNAVAILABLE,
    ]
    assert [contract["stage"] for contract in contracts] == [
        "contract_validation",
        "audit_linkage",
        "executor_runtime",
        "post_execution",
    ]
    assert [contract["retryable"] for contract in contracts] == [
        False,
        False,
        True,
        True,
    ]
    for contract in contracts:
        assert contract["schema_version"] == mutation_executor_service.REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION
        assert contract["tool_name"] == "reindex"
        assert contract["current_surface"] == {
            "kind": "draft_only_not_runtime_reachable",
            "top_level_ok": False,
            "top_level_error_code": tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED,
            "blocked_by": "mutation_apply_guard",
        }
        assert contract["future_failure_surface"] == {
            "kind": "top_level_apply_failure",
            "top_level_ok": False,
            "error_location": "error",
            "error_schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
            "retained_contracts": [
                "mutation_executor",
                "mutation_failure_taxonomy",
            ],
        }
        assert contract["default_behavior"] == "not_emitted_until_actual_live_adapter_execution"


def test_build_reindex_live_failure_contract_preserves_case_details_and_rejects_unknown_code():
    contract = mutation_executor_service.build_reindex_live_failure_contract(
        mutation_executor_service.REINDEX_ERROR_TARGET_MISMATCH,
        details={
            "payload_collection": "all",
            "preview_collection": "fr",
        },
    )

    assert contract is not None
    assert contract["code"] == mutation_executor_service.REINDEX_ERROR_TARGET_MISMATCH
    assert contract["stage"] == "contract_validation"
    assert contract["trigger"] == "payload_apply_preview_target_mismatch"
    assert contract["details"] == {
        "payload_collection": "all",
        "preview_collection": "fr",
    }
    assert mutation_executor_service.build_reindex_live_failure_contract("UNKNOWN_CODE") is None


def test_reindex_boundary_failure_taxonomy_matches_failure_contract_order(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reindex",
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
        )
    )

    failure_taxonomy = result["executor"]["boundary"]["live_adapter_outline"]["failure_taxonomy"]
    assert failure_taxonomy == {
        "schema_version": mutation_executor_service.REINDEX_LIVE_ADAPTER_ERROR_SCHEMA_VERSION,
        "codes": [
            {
                "code": contract["code"],
                "stage": contract["stage"],
                "retryable": contract["retryable"],
            }
            for contract in mutation_executor_service.list_reindex_live_failure_contracts()
        ],
    }


def test_execute_mutation_request_falls_back_to_candidate_stub_when_executor_binding_is_invalid(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reindex",
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
            executor_binding={
                "binding_kind": mutation_executor_service.REINDEX_LIVE_ADAPTER_BINDING_KIND,
                "binding_source": "test_harness",
                "executor_name": "wrong-live-adapter",
            },
        )
    )

    assert result["ok"] is False
    assert result["executor"]["executor_name"] == mutation_executor_service.REINDEX_MUTATION_EXECUTOR_NAME
    assert result["executor"]["selection_state"] == "candidate_stub"
    assert result["executor"]["request"]["executor_binding_present"] is True
    assert result["executor"]["request"]["executor_binding_executor_name"] == "wrong-live-adapter"


def test_execute_mutation_request_keeps_approve_upload_request_in_boundary_noop_even_when_activation_is_requested(
    monkeypatch,
):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "approve_upload_request",
            payload={"request_id": "upload-42"},
            audit_sink_receipt={
                "sink_type": "local_file_append_only",
                "sequence_id": 11,
                "storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            },
            actor="admin",
            actor_category="admin_review_mutation",
        )
    )

    assert result["ok"] is False
    assert result["error"]["code"] == tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED
    assert result["executor"] == {
        "schema_version": mutation_executor_service.MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": "noop_mutation_executor",
        "binding_kind": "default_noop",
        "tool_name": "approve_upload_request",
        "tool_registered": False,
        "activation_requested": True,
        "execution_enabled": False,
        "selection_state": "boundary_noop",
        "selection_reason": "upload_review_scope_deferred",
        "activation": {
            "surface_scope": "internal_service_only",
            "activation_source": "local_env_flag",
            "ownership": "operator_local_config",
            "env_key": mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
            "requested": True,
            "first_live_tool_scope": "reindex",
            "durable_audit_required": False,
            "durable_audit_ready": False,
            "audit_sink_type": "local_file_append_only",
            "audit_sequence_id": 11,
            "audit_storage_path": "/tmp/mutation-audit/audit-20260418.jsonl",
            "blocked_by": [],
        },
        "boundary": {
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
        },
        "request": {
            "request_id": "req-exec-1",
            "actor_category": "admin_review_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
            "apply_schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "audit_record_schema_version": "v1.5.mutation_audit_record.v1",
            "audit_sink_type": "local_file_append_only",
            "executor_binding_present": False,
            "executor_binding_kind": None,
            "executor_binding_source": None,
            "executor_binding_executor_name": None,
            "executor_binding_stage": None,
        },
    }


def test_execute_mutation_request_keeps_reject_upload_request_in_boundary_noop(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(
        _sample_request(
            "reject_upload_request",
            payload={"request_id": "upload-42", "reason": "policy mismatch"},
            actor="admin",
            actor_category="admin_review_mutation",
        )
    )

    assert result["ok"] is False
    assert result["error"]["code"] == tool_apply_service.ERROR_MUTATION_APPLY_NOT_ENABLED
    assert result["executor"] == {
        "schema_version": mutation_executor_service.MUTATION_EXECUTOR_CONTRACT_SCHEMA_VERSION,
        "executor_name": "noop_mutation_executor",
        "binding_kind": "default_noop",
        "tool_name": "reject_upload_request",
        "tool_registered": False,
        "activation_requested": True,
        "execution_enabled": False,
        "selection_state": "boundary_noop",
        "selection_reason": "upload_review_scope_deferred",
        "activation": {
            "surface_scope": "internal_service_only",
            "activation_source": "local_env_flag",
            "ownership": "operator_local_config",
            "env_key": mutation_executor_service.MUTATION_EXECUTION_ENV_KEY,
            "requested": True,
            "first_live_tool_scope": "reindex",
            "durable_audit_required": False,
            "durable_audit_ready": False,
            "audit_sink_type": "null_append_only",
            "audit_sequence_id": None,
            "audit_storage_path": None,
            "blocked_by": [],
        },
        "boundary": {
            "family": "upload_review",
            "classification": "request_decision_only",
            "live_candidate_allowed": False,
            "managed_state_write": False,
            "approval_state_write": True,
            "requires_durable_audit_receipt": True,
            "requires_rollback_plan": False,
            "requires_managed_state_snapshot": False,
            "requires_document_version_binding": False,
            "requires_decision_audit": True,
            "required_preconditions": [
                "separate_upload_review_go_no_go",
                "decision_audit_contract",
            ],
            "blocked_by": [
                "upload_review_scope_deferred",
                "decision_audit_contract_not_reviewed",
            ],
        },
        "request": {
            "request_id": "req-exec-1",
            "actor_category": "admin_review_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
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


def test_list_registered_mutation_executor_bindings_exposes_reindex_stub():
    assert mutation_executor_service.list_registered_mutation_executor_bindings() == {
        "reindex": "reindex_mutation_adapter_stub",
    }
