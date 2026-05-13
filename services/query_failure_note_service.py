from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.settings import PERSIST_DIR, QUERY_FAILURE_NOTE_FILE_NAME

logger = logging.getLogger("doc_rag.api")


def query_failure_note_log_path() -> Path:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    return persist_path / QUERY_FAILURE_NOTE_FILE_NAME


def append_failure_note(record: dict[str, Any]) -> None:
    try:
        note_path = query_failure_note_log_path()
        line = json.dumps(record, ensure_ascii=False)
        with note_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
    except Exception as exc:
        logger.warning("failed to append query failure note: %s", exc)
