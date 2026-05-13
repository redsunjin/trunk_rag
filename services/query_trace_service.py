from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from langchain_core.documents import Document

from core.settings import PERSIST_DIR, QUERY_TRACE_FILE_NAME

logger = logging.getLogger("doc_rag.api")


def query_trace_log_path() -> Path:
    persist_path = Path(PERSIST_DIR)
    persist_path.mkdir(parents=True, exist_ok=True)
    return persist_path / QUERY_TRACE_FILE_NAME


def summarize_docs_for_trace(docs: list[Document], *, max_items: int = 5) -> list[dict[str, Any]]:
    summary: list[dict[str, Any]] = []
    for index, doc in enumerate(docs[:max_items], 1):
        summary.append(
            {
                "rank": index,
                "source": str(doc.metadata.get("source", "unknown")),
                "source_file": str(doc.metadata.get("source_file", "")),
                "h2": str(doc.metadata.get("h2", "")),
                "country": str(doc.metadata.get("country", "")),
                "doc_type": str(doc.metadata.get("doc_type", "")),
                "topic": str(doc.metadata.get("topic", "")),
                "year_text": str(doc.metadata.get("year_text", "")),
                "scientist": str(doc.metadata.get("scientist", "")),
            }
        )
    return summary


def append_query_trace(record: dict[str, Any]) -> None:
    try:
        trace_path = query_trace_log_path()
        line = json.dumps(record, ensure_ascii=False)
        with trace_path.open("a", encoding="utf-8") as file:
            file.write(line + "\n")
    except Exception as exc:
        logger.warning("failed to append query trace: %s", exc)
