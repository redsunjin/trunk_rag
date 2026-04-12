from __future__ import annotations

from fastapi import HTTPException

from services import upload_service

PREVIEW_SEED_SCHEMA_VERSION = "v1.5.mutation_preview_seed.v1"


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _build_reindex_impact_summary(target: dict[str, object]) -> str:
    collection_key = str(target.get("collection_key") or "all")
    reset = bool(target.get("reset"))
    include_compatibility_bundle = bool(target.get("include_compatibility_bundle"))
    if include_compatibility_bundle:
        if reset:
            return f"Reset and reindex {collection_key} plus compatibility bundle collections."
        return f"Reindex {collection_key} plus compatibility bundle collections without reset."
    if reset:
        return f"Reset and reindex {collection_key} collection contents."
    return f"Reindex {collection_key} collection contents without reset."


def _build_reindex_preview(preview_contract: dict[str, object]) -> dict[str, object]:
    target = _safe_dict(preview_contract.get("target"))
    return {
        "collection_key": target.get("collection_key"),
        "reset": target.get("reset"),
        "include_compatibility_bundle": target.get("include_compatibility_bundle"),
        "impact_summary": _build_reindex_impact_summary(target),
    }


def _build_upload_review_preview(preview_contract: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    target = _safe_dict(preview_contract.get("target"))
    request_id = str(target.get("request_id") or "").strip()
    preview = {
        "request_id": request_id or None,
        "status": None,
        "request_type": None,
        "doc_key": None,
        "expected_side_effect": preview_contract.get("expected_side_effect"),
    }
    if not request_id:
        return preview, {"status": "missing_request_id"}

    try:
        request_view = upload_service.get_upload_request_view(request_id)
    except HTTPException:
        return preview, {"status": "request_not_found", "request_id": request_id}

    preview.update(
        {
            "status": request_view.get("status"),
            "request_type": request_view.get("request_type"),
            "doc_key": request_view.get("doc_key"),
        }
    )
    return preview, {"status": "resolved", "request_id": request_id}


def build_preview_seed(
    preview_contract: dict[str, object] | None,
    *,
    payload: dict[str, object] | None = None,
) -> dict[str, object] | None:
    if not isinstance(preview_contract, dict):
        return None

    tool = _safe_dict(preview_contract.get("tool"))
    tool_name = str(tool.get("name") or "").strip()
    if not tool_name:
        return None

    resolution: dict[str, object]
    if tool_name == "reindex":
        preview = _build_reindex_preview(preview_contract)
        resolution = {"status": "resolved"}
    elif tool_name in {"approve_upload_request", "reject_upload_request"}:
        preview, resolution = _build_upload_review_preview(preview_contract)
    else:
        preview = {}
        resolution = {"status": "unsupported_tool"}

    return {
        "schema_version": PREVIEW_SEED_SCHEMA_VERSION,
        "contract_schema_version": preview_contract.get("schema_version"),
        "request_id": preview_contract.get("request_id"),
        "actor_category": preview_contract.get("actor_category"),
        "audit_scope": preview_contract.get("audit_scope"),
        "tool": tool,
        "target": _safe_dict(preview_contract.get("target")),
        "preview_fields": list(preview_contract.get("preview_fields") or []),
        "preview": preview,
        "expected_side_effect": preview_contract.get("expected_side_effect"),
        "resolution": resolution,
        "redaction": _safe_dict(preview_contract.get("redaction")),
    }
