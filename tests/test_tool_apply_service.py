from __future__ import annotations

from services import tool_apply_service, tool_preview_service, tool_trace_service


def _sample_preview_seed() -> dict[str, object]:
    preview_contract = tool_trace_service.build_preview_contract(
        request_id="preview-1",
        tool_name="reindex",
        side_effect="write",
        payload={"collection": "all"},
        policy_details={
            "actor_category": "maintenance_mutation",
            "mutation_candidate_tools": ["reindex"],
            "requires_preview_before_apply": True,
            "audit_scope": "maintenance",
        },
    )
    seed = tool_preview_service.build_preview_seed(preview_contract, payload={"collection": "all"})
    assert seed is not None
    return seed


def _sample_audit_sink_receipt() -> dict[str, object]:
    return {
        "accepted": True,
        "sink_type": "null_append_only",
        "record_schema_version": "v1.5.mutation_audit_record.v1",
        "sequence_id": None,
    }


def test_build_mutation_apply_envelope_includes_preview_audit_and_intent():
    envelope = tool_apply_service.build_mutation_apply_envelope(
        preview_seed=_sample_preview_seed(),
        audit_sink_receipt=_sample_audit_sink_receipt(),
        mutation_intent_summary="reindex all",
    )

    assert envelope == {
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


def test_validate_mutation_apply_envelope_requires_preview_reference():
    result = tool_apply_service.validate_mutation_apply_envelope(
        {"schema_version": tool_apply_service.MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION},
        preview_seed=_sample_preview_seed(),
    )

    assert result == {
        "ok": False,
        "error": {
            "code": tool_apply_service.ERROR_PREVIEW_REFERENCE_REQUIRED,
            "message": "Mutation apply requires preview_ref.",
        },
    }


def test_validate_mutation_apply_envelope_detects_preview_mismatch():
    envelope = tool_apply_service.build_mutation_apply_envelope(
        preview_seed=_sample_preview_seed(),
        audit_sink_receipt=_sample_audit_sink_receipt(),
        mutation_intent_summary="reindex all",
    )
    assert envelope is not None
    envelope["preview_ref"]["target"] = {"collection_key": "fr"}

    result = tool_apply_service.validate_mutation_apply_envelope(
        envelope,
        preview_seed=_sample_preview_seed(),
    )

    assert result == {
        "ok": False,
        "error": {
            "code": tool_apply_service.ERROR_PREVIEW_REFERENCE_MISMATCH,
            "message": "Mutation apply preview_ref does not match the current preview seed.",
        },
    }
