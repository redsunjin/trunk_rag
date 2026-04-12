from __future__ import annotations

from services import tool_preview_service, tool_trace_service


def test_build_preview_seed_for_reindex_resolves_impact_summary():
    preview_contract = tool_trace_service.build_preview_contract(
        request_id="preview-1",
        tool_name="reindex",
        side_effect="write",
        payload={"collection": "all", "reset": True},
        policy_details={
            "actor_category": "maintenance_mutation",
            "mutation_candidate_tools": ["reindex"],
            "requires_preview_before_apply": True,
            "audit_scope": "maintenance",
        },
    )

    seed = tool_preview_service.build_preview_seed(preview_contract, payload={"collection": "all"})

    assert seed == {
        "schema_version": tool_preview_service.PREVIEW_SEED_SCHEMA_VERSION,
        "contract_schema_version": tool_trace_service.PREVIEW_CONTRACT_SCHEMA_VERSION,
        "request_id": "preview-1",
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
        "resolution": {"status": "resolved"},
        "redaction": {
            "audiences": ["internal", "public", "persisted"],
            "raw_content_allowed": False,
            "admin_code_allowed": False,
            "document_body_allowed": False,
        },
    }


def test_build_preview_seed_for_upload_review_reads_safe_request_view(monkeypatch):
    monkeypatch.setattr(
        tool_preview_service.upload_service,
        "get_upload_request_view",
        lambda request_id: {
            "id": request_id,
            "status": "pending",
            "request_type": "update",
            "doc_key": "fr-summary",
            "content_preview": "sensitive preview should not be copied",
        },
    )
    preview_contract = tool_trace_service.build_preview_contract(
        request_id="preview-2",
        tool_name="reject_upload_request",
        side_effect="write",
        payload={"request_id": "upload-42", "reason": "too long"},
        policy_details={
            "actor_category": "admin_review_mutation",
            "mutation_candidate_tools": ["approve_upload_request", "reject_upload_request"],
            "requires_preview_before_apply": True,
            "audit_scope": "mutation_review",
        },
    )

    seed = tool_preview_service.build_preview_seed(preview_contract, payload={"request_id": "upload-42"})

    assert seed["preview"] == {
        "request_id": "upload-42",
        "status": "pending",
        "request_type": "update",
        "doc_key": "fr-summary",
        "expected_side_effect": "Reject a pending upload request without mutating indexed document content.",
    }
    assert seed["resolution"] == {"status": "resolved", "request_id": "upload-42"}
    assert "content_preview" not in seed["preview"]
