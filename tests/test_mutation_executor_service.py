from __future__ import annotations

from services import mutation_executor_service, tool_apply_service


def _sample_request(tool_name: str = "reindex") -> mutation_executor_service.MutationExecutionRequest:
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
    audit_sink_receipt = {
        "sink_type": "null_append_only",
    }
    request = mutation_executor_service.build_mutation_execution_request(
        request_id="req-exec-1",
        tool_name=tool_name,
        payload={"collection": "all"},
        apply_envelope=apply_envelope,
        preview_seed=preview_seed,
        persisted_audit_record=persisted_audit_record,
        audit_sink_receipt=audit_sink_receipt,
        actor="maintenance",
        actor_category="maintenance_mutation",
        allow_mutation=True,
        timeout_seconds=7,
    )
    assert request is not None
    return request


def test_execute_mutation_request_uses_reindex_stub_binding(monkeypatch):
    monkeypatch.delenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, raising=False)

    result = mutation_executor_service.execute_mutation_request(_sample_request("reindex"))

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
        "activation_requested": False,
        "execution_enabled": False,
        "delegate_executor_name": "noop_mutation_executor",
        "request": {
            "request_id": "req-exec-1",
            "actor_category": "maintenance_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
            "apply_schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "audit_record_schema_version": "v1.5.mutation_audit_record.v1",
            "audit_sink_type": "null_append_only",
        },
    }


def test_execute_mutation_request_falls_back_to_default_noop(monkeypatch):
    monkeypatch.setenv(mutation_executor_service.MUTATION_EXECUTION_ENV_KEY, "1")

    result = mutation_executor_service.execute_mutation_request(_sample_request("approve_upload_request"))

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
        "request": {
            "request_id": "req-exec-1",
            "actor_category": "maintenance_mutation",
            "allow_mutation": True,
            "timeout_seconds": 7,
            "apply_schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
            "preview_schema_version": "v1.5.mutation_preview_seed.v1",
            "audit_record_schema_version": "v1.5.mutation_audit_record.v1",
            "audit_sink_type": "null_append_only",
        },
    }


def test_list_registered_mutation_executor_bindings_exposes_reindex_stub():
    assert mutation_executor_service.list_registered_mutation_executor_bindings() == {
        "reindex": "reindex_mutation_adapter_stub",
    }
