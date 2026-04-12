from __future__ import annotations

from services import tool_audit_sink_service, tool_trace_service


def _sample_persisted_audit_record() -> dict[str, object]:
    return {
        "schema_version": tool_trace_service.PERSISTED_AUDIT_RECORD_SCHEMA_VERSION,
        "source_schema_version": tool_trace_service.TRACE_SCHEMA_VERSION,
        "request_id": "req-1",
        "actor_category": "maintenance_mutation",
        "audit_scope": "maintenance",
        "tool": {
            "name": "reindex",
            "side_effect": "write",
        },
        "blocked_by": "mutation_policy_guard",
        "runtime": {
            "elapsed_ms": 5,
        },
        "outcome": {
            "ok": False,
            "error": {"code": "PREVIEW_REQUIRED"},
        },
        "audit": {
            "events": [
                {
                    "event": "tool.invoke.blocked",
                    "elapsed_ms": 5,
                    "code": "PREVIEW_REQUIRED",
                    "tool": "reindex",
                }
            ]
        },
    }


def test_append_persisted_audit_record_accepts_valid_record_with_memory_sink():
    sink = tool_audit_sink_service.InMemoryAppendOnlyAuditSink()

    receipt = tool_audit_sink_service.append_persisted_audit_record(
        _sample_persisted_audit_record(),
        sink=sink,
    )

    assert receipt == {
        "accepted": True,
        "sink_type": "memory_append_only",
        "record_schema_version": tool_trace_service.PERSISTED_AUDIT_RECORD_SCHEMA_VERSION,
        "sequence_id": 1,
    }
    assert sink.list_records() == [_sample_persisted_audit_record()]


def test_append_persisted_audit_record_rejects_sensitive_fields():
    record = _sample_persisted_audit_record()
    record["actor"] = "admin@example.test"

    try:
        tool_audit_sink_service.append_persisted_audit_record(record)
    except ValueError as exc:
        assert "must not contain raw actor" in str(exc)
    else:
        raise AssertionError("expected sensitive actor field to be rejected")
