from __future__ import annotations

MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION = "v1.5.mutation_apply_envelope.v1"

ERROR_PREVIEW_REFERENCE_REQUIRED = "PREVIEW_REFERENCE_REQUIRED"
ERROR_PREVIEW_REFERENCE_MISMATCH = "PREVIEW_REFERENCE_MISMATCH"
ERROR_AUDIT_SINK_RECEIPT_REQUIRED = "AUDIT_SINK_RECEIPT_REQUIRED"
ERROR_AUDIT_SINK_RECEIPT_INVALID = "AUDIT_SINK_RECEIPT_INVALID"
ERROR_MUTATION_INTENT_SUMMARY_REQUIRED = "MUTATION_INTENT_SUMMARY_REQUIRED"
ERROR_MUTATION_APPLY_NOT_ENABLED = "MUTATION_APPLY_NOT_ENABLED"


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _normalize_optional_text(value: object) -> str | None:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def build_mutation_apply_envelope(
    *,
    preview_seed: dict[str, object] | None,
    audit_sink_receipt: dict[str, object] | None,
    mutation_intent_summary: str | None,
) -> dict[str, object] | None:
    if not isinstance(preview_seed, dict) or not isinstance(audit_sink_receipt, dict):
        return None
    tool = _safe_dict(preview_seed.get("tool"))
    if not tool.get("name"):
        return None
    return {
        "schema_version": MUTATION_APPLY_ENVELOPE_SCHEMA_VERSION,
        "actor_category": preview_seed.get("actor_category"),
        "audit_scope": preview_seed.get("audit_scope"),
        "tool": {
            "name": tool.get("name"),
            "side_effect": tool.get("side_effect"),
        },
        "preview_ref": {
            "preview_schema_version": preview_seed.get("schema_version"),
            "tool_name": tool.get("name"),
            "target": _safe_dict(preview_seed.get("target")),
        },
        "audit_ref": {
            "sink_type": audit_sink_receipt.get("sink_type"),
            "record_schema_version": audit_sink_receipt.get("record_schema_version"),
            "accepted": audit_sink_receipt.get("accepted") is True,
            "sequence_id": audit_sink_receipt.get("sequence_id"),
        },
        "intent": {
            "summary": mutation_intent_summary,
        },
        "apply_control": {
            "execution_enabled": False,
            "required_signals": [
                "preview_ref",
                "audit_ref",
                "intent.summary",
            ],
        },
    }


def validate_mutation_apply_envelope(
    envelope: dict[str, object] | None,
    *,
    preview_seed: dict[str, object] | None,
) -> dict[str, object]:
    if not isinstance(envelope, dict):
        return {
            "ok": False,
            "error": {
                "code": ERROR_PREVIEW_REFERENCE_REQUIRED,
                "message": "Mutation apply requires a preview reference envelope.",
            },
        }

    preview_ref = _safe_dict(envelope.get("preview_ref"))
    if not preview_ref:
        return {
            "ok": False,
            "error": {
                "code": ERROR_PREVIEW_REFERENCE_REQUIRED,
                "message": "Mutation apply requires preview_ref.",
            },
        }

    normalized_preview_seed = _safe_dict(preview_seed)
    preview_tool = _safe_dict(normalized_preview_seed.get("tool"))
    expected_target = _safe_dict(normalized_preview_seed.get("target"))
    if (
        preview_ref.get("preview_schema_version") != normalized_preview_seed.get("schema_version")
        or preview_ref.get("tool_name") != preview_tool.get("name")
        or _safe_dict(preview_ref.get("target")) != expected_target
        or envelope.get("actor_category") != normalized_preview_seed.get("actor_category")
    ):
        return {
            "ok": False,
            "error": {
                "code": ERROR_PREVIEW_REFERENCE_MISMATCH,
                "message": "Mutation apply preview_ref does not match the current preview seed.",
            },
        }

    audit_ref = _safe_dict(envelope.get("audit_ref"))
    if not audit_ref:
        return {
            "ok": False,
            "error": {
                "code": ERROR_AUDIT_SINK_RECEIPT_REQUIRED,
                "message": "Mutation apply requires audit_ref.",
            },
        }
    if (
        audit_ref.get("accepted") is not True
        or _normalize_optional_text(audit_ref.get("sink_type")) is None
        or _normalize_optional_text(audit_ref.get("record_schema_version")) is None
    ):
        return {
            "ok": False,
            "error": {
                "code": ERROR_AUDIT_SINK_RECEIPT_INVALID,
                "message": "Mutation apply requires a valid accepted audit sink receipt.",
            },
        }

    intent = _safe_dict(envelope.get("intent"))
    if _normalize_optional_text(intent.get("summary")) is None:
        return {
            "ok": False,
            "error": {
                "code": ERROR_MUTATION_INTENT_SUMMARY_REQUIRED,
                "message": "Mutation apply requires intent.summary.",
            },
        }

    return {
        "ok": True,
        "envelope": dict(envelope),
    }
