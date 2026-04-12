from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

from services import tool_trace_service


class AppendOnlyAuditSink(Protocol):
    sink_type: str

    def append(self, record: dict[str, object]) -> dict[str, object]:
        ...


@dataclass
class NullAppendOnlyAuditSink:
    sink_type: str = "null_append_only"

    def append(self, record: dict[str, object]) -> dict[str, object]:
        return {
            "accepted": True,
            "sink_type": self.sink_type,
            "record_schema_version": record.get("schema_version"),
            "sequence_id": None,
        }


@dataclass
class InMemoryAppendOnlyAuditSink:
    sink_type: str = "memory_append_only"
    records: list[dict[str, object]] = field(default_factory=list)

    def append(self, record: dict[str, object]) -> dict[str, object]:
        self.records.append(dict(record))
        return {
            "accepted": True,
            "sink_type": self.sink_type,
            "record_schema_version": record.get("schema_version"),
            "sequence_id": len(self.records),
        }

    def list_records(self) -> list[dict[str, object]]:
        return [dict(record) for record in self.records]


DEFAULT_APPEND_ONLY_AUDIT_SINK: AppendOnlyAuditSink = NullAppendOnlyAuditSink()


def _safe_dict(value: object) -> dict[str, object]:
    return dict(value) if isinstance(value, dict) else {}


def _safe_list_of_dicts(value: object) -> list[dict[str, object]]:
    if not isinstance(value, list):
        return []
    return [dict(item) for item in value if isinstance(item, dict)]


def validate_persisted_audit_record(record: dict[str, object]) -> dict[str, object]:
    if not isinstance(record, dict):
        raise TypeError("persisted audit record must be an object.")
    if record.get("schema_version") != tool_trace_service.PERSISTED_AUDIT_RECORD_SCHEMA_VERSION:
        raise ValueError("unsupported persisted audit record schema version.")
    if "actor" in record or "raw_payload" in record:
        raise ValueError("persisted audit record must not contain raw actor or payload fields.")

    tool = _safe_dict(record.get("tool"))
    if not tool.get("name") or not tool.get("side_effect"):
        raise ValueError("persisted audit record must include tool name and side_effect.")

    outcome = _safe_dict(record.get("outcome"))
    if "ok" not in outcome:
        raise ValueError("persisted audit record must include outcome.ok.")
    if isinstance(outcome.get("error"), dict) and "message" in outcome["error"]:
        raise ValueError("persisted audit record must not contain raw error messages.")

    audit = _safe_dict(record.get("audit"))
    events = _safe_list_of_dicts(audit.get("events"))
    for event in events:
        if "actor" in event or "admin_code" in event:
            raise ValueError("persisted audit events must not contain actor or admin code.")

    return dict(record)


def append_persisted_audit_record(
    record: dict[str, object],
    *,
    sink: AppendOnlyAuditSink | None = None,
) -> dict[str, object]:
    validated_record = validate_persisted_audit_record(record)
    resolved_sink = sink or DEFAULT_APPEND_ONLY_AUDIT_SINK
    return resolved_sink.append(validated_record)
