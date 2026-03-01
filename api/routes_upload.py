from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from langchain_core.documents import Document

from api.schemas import UploadRequestApproveAction, UploadRequestCreateRequest, UploadRequestRejectAction
from core.settings import (
    DEFAULT_COLLECTION_KEY,
    REQUEST_STATUS_APPROVED,
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_REJECTED,
    UPLOAD_REQUEST_LOCK,
)
from scripts.validate_rag_doc import validate_markdown_text
from services import collection_service, index_service, runtime_service, upload_service

router = APIRouter()


@router.get("/upload-requests/{request_id}")
def upload_request_detail(request_id: str) -> dict[str, object]:
    with UPLOAD_REQUEST_LOCK:
        _items, item, _index = upload_service.find_upload_request(request_id)
    return {"request": item}


@router.post("/upload-requests")
def create_upload_request(req: UploadRequestCreateRequest) -> dict[str, object]:
    collection_key = upload_service.resolve_requested_collection_key(req.collection)

    source_seed = req.source_name or f"upload_{int(time.time())}"
    try:
        source_name = runtime_service.sanitize_source_name(source_seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="source_name is required.") from exc

    metadata = upload_service.build_upload_request_metadata(
        source_name=source_name,
        collection_key=collection_key,
        country=req.country,
        doc_type=req.doc_type,
    )
    validation = validate_markdown_text(
        source=source_name,
        text=req.content,
        metadata=metadata,
    )

    now = runtime_service.utc_now_iso()
    request_item: dict[str, object] = {
        "id": str(uuid4()),
        "status": REQUEST_STATUS_PENDING,
        "collection_key": collection_key,
        "collection": collection_service.get_collection_name(collection_key),
        "source_name": source_name,
        "content": req.content,
        "metadata": metadata,
        "validation": validation,
        "usable": bool(validation.get("usable", False)),
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "rejected_at": None,
        "rejected_reason": None,
        "ingest": None,
    }

    auto_approve = runtime_service.is_auto_approve_enabled()
    if auto_approve:
        if not request_item["usable"]:
            request_item["status"] = REQUEST_STATUS_REJECTED
            request_item["rejected_at"] = now
            request_item["rejected_reason"] = "auto-approve enabled but validation failed"
        else:
            metadata_obj = request_item["metadata"]
            if not isinstance(metadata_obj, dict):
                metadata_obj = {}

            ingest_result = index_service.index_documents_for_collection(
                [
                    Document(
                        page_content=req.content,
                        metadata=metadata_obj,
                    )
                ],
                collection_key=collection_key,
                reset=False,
            )
            request_item["status"] = REQUEST_STATUS_APPROVED
            request_item["approved_at"] = now
            request_item["ingest"] = ingest_result
        request_item["updated_at"] = now

    with UPLOAD_REQUEST_LOCK:
        items = upload_service._load_upload_requests_unlocked()
        items.append(request_item)
        upload_service._save_upload_requests_unlocked(items)

    return {"auto_approve": auto_approve, "request": request_item}


@router.post("/upload-requests/{request_id}/approve")
def approve_upload_request(request_id: str, action: UploadRequestApproveAction) -> dict[str, object]:
    runtime_service.verify_admin_code(action.code)

    with UPLOAD_REQUEST_LOCK:
        items, item, index = upload_service.find_upload_request(request_id)
        upload_service.ensure_pending_status(item)

        usable = bool(item.get("usable", False))
        if not usable:
            raise HTTPException(
                status_code=400,
                detail="Validation failed request cannot be approved. Check request.validation.reasons.",
            )

        try:
            collection_key = collection_service.resolve_collection_key(
                action.collection or str(item.get("collection_key", ""))
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Unsupported collection.") from exc

        if collection_key is None:
            collection_key = DEFAULT_COLLECTION_KEY

        metadata_obj = item.get("metadata", {})
        if not isinstance(metadata_obj, dict):
            metadata_obj = {}

        ingest_result = index_service.index_documents_for_collection(
            [
                Document(
                    page_content=str(item.get("content", "")),
                    metadata=metadata_obj,
                )
            ],
            collection_key=collection_key,
            reset=False,
        )

        now = runtime_service.utc_now_iso()
        item["status"] = REQUEST_STATUS_APPROVED
        item["collection_key"] = collection_key
        item["collection"] = collection_service.get_collection_name(collection_key)
        item["approved_at"] = now
        item["updated_at"] = now
        item["rejected_at"] = None
        item["rejected_reason"] = None
        item["ingest"] = ingest_result
        items[index] = item
        upload_service._save_upload_requests_unlocked(items)

    return {"request": item}


@router.post("/upload-requests/{request_id}/reject")
def reject_upload_request(request_id: str, action: UploadRequestRejectAction) -> dict[str, object]:
    runtime_service.verify_admin_code(action.code)

    with UPLOAD_REQUEST_LOCK:
        items, item, index = upload_service.find_upload_request(request_id)
        upload_service.ensure_pending_status(item)

        now = runtime_service.utc_now_iso()
        item["status"] = REQUEST_STATUS_REJECTED
        item["rejected_reason"] = action.reason.strip()
        item["rejected_at"] = now
        item["updated_at"] = now
        item["approved_at"] = None
        item["ingest"] = None
        items[index] = item
        upload_service._save_upload_requests_unlocked(items)

    return {"request": item}
