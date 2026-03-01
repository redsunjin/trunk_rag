from __future__ import annotations

import json
from pathlib import Path

from fastapi import HTTPException

from core.settings import (
    DEFAULT_COLLECTION_KEY,
    PERSIST_DIR,
    REQUEST_STATUS_PENDING,
    UPLOAD_REQUEST_LOCK,
    UPLOAD_REQUEST_STORE_FILE,
)
from services import collection_service


def upload_request_store_path() -> Path:
    path = Path(PERSIST_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path / UPLOAD_REQUEST_STORE_FILE


def _load_upload_requests_unlocked() -> list[dict[str, object]]:
    path = upload_request_store_path()
    if not path.exists():
        return []

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []

    if isinstance(payload, dict) and isinstance(payload.get("items"), list):
        return payload["items"]
    if isinstance(payload, list):
        return payload
    return []


def _save_upload_requests_unlocked(items: list[dict[str, object]]) -> None:
    path = upload_request_store_path()
    payload = {"items": items}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_upload_requests(
    status: str | None = None,
    reason: str | None = None,
    search: str | None = None,
) -> list[dict[str, object]]:
    with UPLOAD_REQUEST_LOCK:
        items = _load_upload_requests_unlocked()

    if status:
        value = status.strip().lower()
        items = [item for item in items if str(item.get("status", "")).lower() == value]

    if reason:
        reason_query = reason.strip().lower()
        if reason_query:
            items = [
                item
                for item in items
                if reason_query in str(item.get("rejected_reason", "")).strip().lower()
            ]

    if search:
        query = search.strip().lower()
        if query:
            items = [
                item
                for item in items
                if query in str(item.get("id", "")).lower()
                or query in str(item.get("source_name", "")).lower()
                or query in str(item.get("collection_key", "")).lower()
                or query in str(item.get("status", "")).lower()
                or query in str(item.get("rejected_reason", "")).lower()
            ]

    return sorted(items, key=lambda item: str(item.get("created_at", "")), reverse=True)


def find_upload_request(request_id: str) -> tuple[list[dict[str, object]], dict[str, object], int]:
    items = _load_upload_requests_unlocked()
    for index, item in enumerate(items):
        if item.get("id") == request_id:
            return items, item, index
    raise HTTPException(status_code=404, detail=f"Upload request not found: {request_id}")


def ensure_pending_status(item: dict[str, object]) -> None:
    status = str(item.get("status", ""))
    if status != REQUEST_STATUS_PENDING:
        raise HTTPException(status_code=400, detail=f"Request is not pending. status={status}")


def build_upload_request_metadata(
    *,
    source_name: str,
    collection_key: str,
    country: str | None,
    doc_type: str | None,
) -> dict[str, str]:
    metadata_country = (country or "").strip() or collection_service.default_country_for_collection(collection_key)
    metadata_doc_type = (doc_type or "").strip() or collection_service.default_doc_type_for_collection(collection_key)
    return {
        "source": source_name,
        "country": metadata_country,
        "doc_type": metadata_doc_type,
    }


def resolve_requested_collection_key(collection: str | None) -> str:
    try:
        return collection_service.resolve_collection_key(collection) or DEFAULT_COLLECTION_KEY
    except ValueError as exc:
        supported = ", ".join(collection_service.list_collection_keys())
        raise HTTPException(status_code=400, detail=f"Unsupported collection. Use one of: {supported}") from exc
