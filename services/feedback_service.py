from __future__ import annotations

import json
import threading
import uuid
from pathlib import Path
from typing import Any

from core.settings import PERSIST_DIR
from services.runtime_service import utc_now_iso

QUERY_FEEDBACK_STORE_FILE = "query_feedback.jsonl"
_FEEDBACK_LOCK = threading.RLock()


def query_feedback_store_path() -> Path:
    return Path(PERSIST_DIR) / QUERY_FEEDBACK_STORE_FILE


def append_feedback(payload: dict[str, Any]) -> dict[str, Any]:
    feedback_id = str(uuid.uuid4())
    record = {
        "id": feedback_id,
        "created_at": utc_now_iso(),
        **payload,
    }
    path = query_feedback_store_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(record, ensure_ascii=False, sort_keys=True)
    with _FEEDBACK_LOCK:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(line + "\n")
    return {
        "id": feedback_id,
        "storage": str(path),
        "record": record,
    }
