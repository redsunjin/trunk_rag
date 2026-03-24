from __future__ import annotations

from fastapi import APIRouter, HTTPException

from api.schemas import AdminAuthRequest, ReindexRequest
from core.settings import DEFAULT_COLLECTION_KEY, PERSIST_DIR, REQUEST_STATUS_PENDING, REQUEST_STATUSES
from services import collection_service, index_service, runtime_service, upload_service

router = APIRouter()


@router.get("/health")
def health() -> dict[str, object]:
    default_collection = collection_service.get_collection_name(DEFAULT_COLLECTION_KEY)
    pending_count = len(upload_service.list_upload_requests(status=REQUEST_STATUS_PENDING))
    chunking = runtime_service.get_chunking_config()
    default_llm = runtime_service.get_default_llm_config()
    query_timeout_seconds = runtime_service.get_query_timeout_seconds()
    vectors = index_service.get_vector_count_fast(default_collection) or 0
    runtime_budget = runtime_service.plan_query_budget(
        provider=str(default_llm["provider"] or "ollama"),
        model=str(default_llm["model"] or "") or None,
        timeout_seconds=query_timeout_seconds,
        collection_count=1,
        route_reason="default",
    )
    embedding_status = index_service.get_embedding_fingerprint_status()
    release_web = runtime_service.build_release_web_guidance(
        vectors=vectors,
        default_llm_provider=str(default_llm["provider"] or "ollama"),
        default_llm_model=str(default_llm["model"] or "") or None,
        default_llm_base_url=str(default_llm["base_url"] or "") or None,
        query_timeout_seconds=query_timeout_seconds,
        embedding_model=runtime_service.get_embedding_model(),
    )
    return {
        "status": "ok",
        "collection_key": DEFAULT_COLLECTION_KEY,
        "collection": default_collection,
        "persist_dir": PERSIST_DIR,
        "vectors": vectors,
        "auto_approve": runtime_service.is_auto_approve_enabled(),
        "pending_requests": pending_count,
        "chunking_mode": chunking["mode"],
        "embedding_model": runtime_service.get_embedding_model(),
        "query_timeout_seconds": query_timeout_seconds,
        "max_context_chars": runtime_service.get_max_context_chars(),
        "default_llm_provider": default_llm["provider"],
        "default_llm_model": default_llm["model"],
        "default_llm_base_url": default_llm["base_url"],
        "runtime_profile_status": release_web["runtime_profile"]["status"],
        "runtime_profile_scope": release_web["runtime_profile"]["scope"],
        "runtime_profile_message": release_web["runtime_profile"]["message"],
        "runtime_profile_recommendation": release_web["runtime_profile"]["recommendation"],
        "runtime_query_budget_profile": runtime_budget["profile"],
        "runtime_query_budget_summary": runtime_budget["summary"],
        "embedding_fingerprint_status": embedding_status["status"],
        "embedding_fingerprint_message": embedding_status["message"],
        "embedding_fingerprint_details": embedding_status["items"],
        "release_web_status": release_web["status"],
        "release_web_headline": release_web["headline"],
        "release_web_steps": release_web["steps"],
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
