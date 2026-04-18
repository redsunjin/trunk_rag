from __future__ import annotations

from pathlib import Path

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


def test_local_file_append_only_audit_sink_persists_sequence_and_metadata(tmp_path):
    sink = tool_audit_sink_service.LocalFileAppendOnlyAuditSink(root_dir=tmp_path / "mutation_audit")

    first = tool_audit_sink_service.append_persisted_audit_record(
        _sample_persisted_audit_record(),
        sink=sink,
    )
    second = tool_audit_sink_service.append_persisted_audit_record(
        _sample_persisted_audit_record(),
        sink=sink,
    )

    assert first["accepted"] is True
    assert first["sink_type"] == "local_file_append_only"
    assert first["record_schema_version"] == tool_trace_service.PERSISTED_AUDIT_RECORD_SCHEMA_VERSION
    assert first["sequence_id"] == 1
    assert Path(str(first["storage_path"])).exists() is True
    assert first["rotation_unit"] == "day"
    assert first["prune_policy"] == "rolling_window"
    assert first["retention_days"] == 90
    assert second["sequence_id"] == 2
    assert second["sink_type"] == "local_file_append_only"
    entries = sink.list_entries()
    assert [entry["sequence_id"] for entry in entries] == [1, 2]
    assert all(entry["record"]["request_id"] == "req-1" for entry in entries)


def test_append_persisted_audit_record_uses_local_file_backend_when_configured(tmp_path, monkeypatch):
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_BACKEND_ENV_KEY, "local_file")
    monkeypatch.setenv(tool_audit_sink_service.AUDIT_SINK_DIR_ENV_KEY, str(tmp_path / "configured_audit"))

    receipt = tool_audit_sink_service.append_persisted_audit_record(_sample_persisted_audit_record())

    assert receipt["accepted"] is True
    assert receipt["sink_type"] == "local_file_append_only"
    assert receipt["sequence_id"] == 1
    assert receipt["rotation_unit"] == "day"
    assert receipt["prune_policy"] == "rolling_window"
    assert receipt["retention_days"] == 90
    assert Path(str(receipt["storage_path"])).exists() is True
