from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import AdminAuthRequest, ReindexRequest
from core.settings import DEFAULT_COLLECTION_KEY, PERSIST_DIR, REQUEST_STATUS_PENDING, REQUEST_STATUSES
from services import collection_service, index_service, runtime_service, upload_service

router = APIRouter()


@router.get("/health")
def health() -> dict[str, int | str | bool | None]:
    default_collection = collection_service.get_collection_name(DEFAULT_COLLECTION_KEY)
    pending_count = len(upload_service.list_upload_requests(status=REQUEST_STATUS_PENDING))
    chunking = runtime_service.get_chunking_config()
    return {
        "status": "ok",
        "collection_key": DEFAULT_COLLECTION_KEY,
        "collection": default_collection,
        "persist_dir": PERSIST_DIR,
        "vectors": index_service.get_vector_count_fast(default_collection),
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "pending_requests": pending_count,
        "chunking_mode": chunking["mode"],
        "query_timeout_seconds": runtime_service.get_query_timeout_seconds(),
        "max_context_chars": runtime_service.get_max_context_chars(),
    }


@router.get("/collections")
def collections() -> dict[str, object]:
    return {
        "default_collection_key": DEFAULT_COLLECTION_KEY,
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "collections": collection_service.list_collection_statuses(index_service.get_vector_count_fast),
    }


@router.get("/upload-requests")
def upload_requests(
    status: str | None = None,
    reason: str | None = None,
    q: str | None = None,
) -> dict[str, object]:
    if status:
        value = status.strip().lower()
        if value not in REQUEST_STATUSES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported status. Use one of: {', '.join(sorted(REQUEST_STATUSES))}",
            )

    items = upload_service.list_upload_requests(status=status, reason=reason, search=q)
    counts = {
        "pending": 0,
        "approved": 0,
        "rejected": 0,
    }
    for item in upload_service.list_upload_requests(status=None):
        current = str(item.get("status", "")).lower()
        if current in counts:
            counts[current] += 1

    return {
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "counts": counts,
        "requests": items,
    }


@router.post("/reindex")
def reindex_endpoint(req: ReindexRequest) -> dict[str, object]:
    try:
        collection_key = collection_service.resolve_collection_key(req.collection) or DEFAULT_COLLECTION_KEY
    except ValueError as exc:
        supported = ", ".join(collection_service.list_collection_keys())
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported collection. Use one of: {supported}",
        ) from exc
    return index_service.reindex(reset=req.reset, collection_key=collection_key)


@router.post("/admin/auth")
def admin_auth(req: AdminAuthRequest) -> dict[str, bool]:
    runtime_service.verify_admin_code(req.code)
    return {"ok": True}
