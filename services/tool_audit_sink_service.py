from __future__ import annotations

from dataclasses import dataclass, field
import json
import os
from pathlib import Path
from typing import Protocol

from common import default_persist_dir
from services import runtime_service, tool_trace_service

AUDIT_SINK_BACKEND_ENV_KEY = "DOC_RAG_MUTATION_AUDIT_BACKEND"
AUDIT_SINK_DIR_ENV_KEY = "DOC_RAG_MUTATION_AUDIT_DIR"
AUDIT_SINK_BACKEND_NULL = "null"
AUDIT_SINK_BACKEND_MEMORY = "memory"
AUDIT_SINK_BACKEND_LOCAL_FILE = "local_file"
DEFAULT_AUDIT_RETENTION_DAYS = 90
DEFAULT_AUDIT_ROTATION_UNIT = "day"


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


@dataclass
class LocalFileAppendOnlyAuditSink:
    root_dir: Path
    sink_type: str = "local_file_append_only"
    retention_days: int = DEFAULT_AUDIT_RETENTION_DAYS
    rotation_unit: str = DEFAULT_AUDIT_ROTATION_UNIT

    def _ensure_root_dir(self) -> None:
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _sequence_state_path(self) -> Path:
        return self.root_dir / "sequence_state.json"

    def _log_path(self) -> Path:
        date_token = runtime_service.utc_now_iso().split("T", 1)[0].replace("-", "")
        return self.root_dir / f"audit-{date_token}.jsonl"

    def _next_sequence_id(self) -> int:
        state_path = self._sequence_state_path()
        last_sequence_id = 0
        if state_path.exists():
            try:
                state = json.loads(state_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                state = {}
            if isinstance(state, dict):
                raw_value = state.get("last_sequence_id", 0)
                try:
                    last_sequence_id = int(raw_value)
                except (TypeError, ValueError):
                    last_sequence_id = 0
        next_sequence_id = last_sequence_id + 1
        state_path.write_text(
            json.dumps(
                {
                    "last_sequence_id": next_sequence_id,
                    "updated_at": runtime_service.utc_now_iso(),
                },
                ensure_ascii=False,
                indent=2,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        return next_sequence_id

    def append(self, record: dict[str, object]) -> dict[str, object]:
        self._ensure_root_dir()
        sequence_id = self._next_sequence_id()
        written_at = runtime_service.utc_now_iso()
        storage_path = self._log_path()
        entry = {
            "sequence_id": sequence_id,
            "written_at": written_at,
            "rotation_unit": self.rotation_unit,
            "prune_policy": "rolling_window",
            "retention_days": self.retention_days,
            "record": dict(record),
        }
        with storage_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False, sort_keys=True) + "\n")
        return {
            "accepted": True,
            "sink_type": self.sink_type,
            "record_schema_version": record.get("schema_version"),
            "sequence_id": sequence_id,
            "storage_path": str(storage_path),
            "rotation_unit": self.rotation_unit,
            "prune_policy": "rolling_window",
            "retention_days": self.retention_days,
        }

    def list_entries(self) -> list[dict[str, object]]:
        if not self.root_dir.exists():
            return []
        entries: list[dict[str, object]] = []
        for path in sorted(self.root_dir.glob("audit-*.jsonl")):
            for raw_line in path.read_text(encoding="utf-8").splitlines():
                if not raw_line.strip():
                    continue
                entries.append(json.loads(raw_line))
        return entries


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


def default_audit_sink_root_dir() -> Path:
    return default_persist_dir() / "mutation_audit"


def resolve_append_only_audit_sink(
    *,
    backend: str | None = None,
    root_dir: str | Path | None = None,
) -> AppendOnlyAuditSink:
    resolved_backend = (backend or "").strip().lower() or AUDIT_SINK_BACKEND_NULL
    if resolved_backend in {AUDIT_SINK_BACKEND_NULL, "null_append_only"}:
        return NullAppendOnlyAuditSink()
    if resolved_backend in {AUDIT_SINK_BACKEND_MEMORY, "memory_append_only"}:
        return InMemoryAppendOnlyAuditSink()
    if resolved_backend in {AUDIT_SINK_BACKEND_LOCAL_FILE, "local_file_append_only"}:
        resolved_root_dir = Path(root_dir) if root_dir is not None else default_audit_sink_root_dir()
        return LocalFileAppendOnlyAuditSink(root_dir=resolved_root_dir)
    raise ValueError(f"unsupported append-only audit backend: {backend}")


def get_configured_append_only_audit_sink() -> AppendOnlyAuditSink:
    backend_name = os.getenv(AUDIT_SINK_BACKEND_ENV_KEY, AUDIT_SINK_BACKEND_NULL).strip().lower()
    root_dir = os.getenv(AUDIT_SINK_DIR_ENV_KEY, "").strip() or None
    return resolve_append_only_audit_sink(backend=backend_name, root_dir=root_dir)


def append_persisted_audit_record(
    record: dict[str, object],
    *,
    sink: AppendOnlyAuditSink | None = None,
) -> dict[str, object]:
    validated_record = validate_persisted_audit_record(record)
    resolved_sink = sink or get_configured_append_only_audit_sink()
    return resolved_sink.append(validated_record)
