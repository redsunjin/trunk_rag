from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException

from core.settings import (
    DEFAULT_COLLECTION_KEY,
    PERSIST_DIR,
    REQUEST_STATUS_PENDING,
    UPLOAD_REQUEST_LOCK,
    UPLOAD_REQUEST_STORE_FILE,
)
from services import runtime_service
from services import collection_service

REQUEST_TYPE_CREATE = "create"
REQUEST_TYPE_UPDATE = "update"
REQUEST_TYPES = {REQUEST_TYPE_CREATE, REQUEST_TYPE_UPDATE}
MANAGED_DOCS_DIR = "managed_docs"
MANAGED_DOCS_MANIFEST_FILE = "manifest.json"


def upload_request_store_path() -> Path:
    path = Path(PERSIST_DIR)
    path.mkdir(parents=True, exist_ok=True)
    return path / UPLOAD_REQUEST_STORE_FILE


def managed_doc_store_dir() -> Path:
    path = Path(PERSIST_DIR) / MANAGED_DOCS_DIR
    path.mkdir(parents=True, exist_ok=True)
    return path


def managed_doc_manifest_path() -> Path:
    return managed_doc_store_dir() / MANAGED_DOCS_MANIFEST_FILE


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


def _load_managed_docs_unlocked() -> list[dict[str, object]]:
    path = managed_doc_manifest_path()
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


def _save_managed_docs_unlocked(items: list[dict[str, object]]) -> None:
    path = managed_doc_manifest_path()
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
                or query in str(item.get("doc_key", "")).lower()
                or query in str(item.get("request_type", "")).lower()
                or query in str(item.get("collection_key", "")).lower()
                or query in str(item.get("status", "")).lower()
                or query in str(item.get("change_summary", "")).lower()
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


def build_doc_key(*, doc_key: str | None, source_name: str) -> str:
    seed = doc_key or Path(source_name).stem
    return runtime_service.sanitize_doc_key(seed)


def seed_doc_keys_for_collection(collection_key: str) -> list[str]:
    config = collection_service.get_collection_config(collection_key)
    file_names = config.get("file_names", [])
    return [Path(str(name)).stem.lower() for name in file_names]


def _list_active_managed_docs_unlocked(collection_key: str | None = None) -> list[dict[str, object]]:
    items = [item for item in _load_managed_docs_unlocked() if bool(item.get("active", False))]
    if collection_key is None:
        return items
    return [item for item in items if str(item.get("collection_key", "")) == collection_key]


def list_active_managed_docs(collection_key: str | None = None) -> list[dict[str, object]]:
    with UPLOAD_REQUEST_LOCK:
        return _list_active_managed_docs_unlocked(collection_key)


def doc_key_exists_unlocked(collection_key: str, doc_key: str) -> bool:
    if doc_key in seed_doc_keys_for_collection(collection_key):
        return True
    for item in _list_active_managed_docs_unlocked(collection_key):
        if str(item.get("doc_key", "")).lower() == doc_key:
            return True
    return False


def resolve_request_type(request_type: str | None, *, collection_key: str, doc_key: str) -> str:
    exists = doc_key_exists_unlocked(collection_key, doc_key)
    if request_type:
        value = request_type.strip().lower()
        if value not in REQUEST_TYPES:
            supported = ", ".join(sorted(REQUEST_TYPES))
            raise HTTPException(status_code=422, detail=f"Unsupported request_type. Use one of: {supported}")
        if value == REQUEST_TYPE_CREATE and exists:
            raise HTTPException(status_code=422, detail=f"doc_key already exists for collection: {doc_key}")
        if value == REQUEST_TYPE_UPDATE and not exists:
            raise HTTPException(status_code=422, detail=f"doc_key not found for update: {doc_key}")
        return value

    return REQUEST_TYPE_UPDATE if exists else REQUEST_TYPE_CREATE


def affected_collection_keys(collection_key: str) -> list[str]:
    keys = [collection_key]
    if collection_key != DEFAULT_COLLECTION_KEY:
        keys.append(DEFAULT_COLLECTION_KEY)
    return collection_service.dedupe_collection_keys(keys)


def _compact_timestamp(now: str) -> str:
    return (
        now.replace(":", "")
        .replace("-", "")
        .replace("+", "_")
        .replace("T", "_")
    )


def save_managed_doc_version_unlocked(
    *,
    request_item: dict[str, object],
    collection_key: str,
    now: str,
) -> dict[str, object]:
    items = _load_managed_docs_unlocked()
    doc_key = str(request_item.get("doc_key", "")).lower()
    source_name = str(request_item.get("source_name", "managed_doc.md"))
    metadata = request_item.get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}

    superseded_version_id = None
    for item in items:
        if not bool(item.get("active", False)):
            continue
        if str(item.get("collection_key", "")) != collection_key:
            continue
        if str(item.get("doc_key", "")).lower() != doc_key:
            continue
        item["active"] = False
        item["updated_at"] = now
        superseded_version_id = item.get("version_id")

    version_id = str(uuid4())
    target_dir = managed_doc_store_dir() / collection_key / doc_key
    target_dir.mkdir(parents=True, exist_ok=True)
    file_name = f"{_compact_timestamp(now)}_{version_id[:8]}_{source_name}"
    target_path = target_dir / file_name
    target_path.write_text(str(request_item.get("content", "")), encoding="utf-8")

    entry = {
        "version_id": version_id,
        "active": True,
        "collection_key": collection_key,
        "doc_key": doc_key,
        "source_name": source_name,
        "file_path": str(target_path),
        "request_id": request_item.get("id"),
        "request_type": request_item.get("request_type", REQUEST_TYPE_CREATE),
        "change_summary": request_item.get("change_summary") or "",
        "metadata": metadata,
        "created_at": now,
        "updated_at": now,
        "superseded_version_id": superseded_version_id,
    }
    items.append(entry)
    _save_managed_docs_unlocked(items)
    return entry


def resolve_requested_collection_key(collection: str | None) -> str:
    try:
        return collection_service.resolve_collection_key(collection) or DEFAULT_COLLECTION_KEY
    except ValueError as exc:
        supported = ", ".join(collection_service.list_collection_keys())
        raise HTTPException(status_code=400, detail=f"Unsupported collection. Use one of: {supported}") from exc
