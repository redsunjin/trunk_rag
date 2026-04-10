from __future__ import annotations

import time
from uuid import uuid4

from fastapi import APIRouter, HTTPException

from api.schemas import UploadRequestApproveAction, UploadRequestCreateRequest, UploadRequestRejectAction
from core.settings import (
    REQUEST_STATUS_PENDING,
    REQUEST_STATUS_REJECTED,
    UPLOAD_REQUEST_LOCK,
)
from scripts.validate_rag_doc import validate_markdown_text
from services import collection_service, runtime_service, upload_service

router = APIRouter()


def _view_request_item(request_item: dict[str, object]) -> dict[str, object]:
    return upload_service.build_upload_request_view_unlocked(request_item)


@router.get("/upload-requests/{request_id}")
def upload_request_detail(request_id: str) -> dict[str, object]:
    with UPLOAD_REQUEST_LOCK:
        _items, item, _index = upload_service.find_upload_request(request_id)
    return {"request": _view_request_item(item)}


@router.post("/upload-requests")
def create_upload_request(req: UploadRequestCreateRequest) -> dict[str, object]:
    collection_key = upload_service.resolve_requested_collection_key(req.collection)

    source_seed = req.source_name or f"upload_{int(time.time())}"
    try:
        source_name = runtime_service.sanitize_source_name(source_seed)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="source_name is required.") from exc
    try:
        doc_key = upload_service.build_doc_key(doc_key=req.doc_key, source_name=source_name)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="doc_key is required.") from exc

    change_summary = (req.change_summary or "").strip()

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
        "request_type": None,
        "doc_key": doc_key,
        "change_summary": change_summary,
        "content": req.content,
        "metadata": metadata,
        "validation": validation,
        "usable": bool(validation.get("usable", False)),
        "created_at": now,
        "updated_at": now,
        "approved_at": None,
        "rejected_at": None,
        "rejected_reason_code": None,
        "rejected_reason": None,
        "decision_note": None,
        "rejected_reason_note": None,
        "managed_doc": None,
        "ingest": None,
    }

    with UPLOAD_REQUEST_LOCK:
        request_type = upload_service.resolve_request_type(
            req.request_type,
            collection_key=collection_key,
            doc_key=doc_key,
        )
        request_item["request_type"] = request_type

        auto_approve = runtime_service.is_auto_approve_enabled() and request_type == upload_service.REQUEST_TYPE_CREATE
        if auto_approve:
            auto_now = runtime_service.utc_now_iso()
            if not request_item["usable"]:
                request_item["status"] = REQUEST_STATUS_REJECTED
                request_item["rejected_at"] = auto_now
                request_item["rejected_reason_code"] = "VALIDATION"
                request_item["rejected_reason"] = "auto-approve enabled but validation failed"
                request_item["decision_note"] = "auto-approve enabled but validation failed"
                request_item["rejected_reason_note"] = "auto-approve enabled but validation failed"
                request_item["updated_at"] = auto_now
            else:
                upload_service.approve_request_item_unlocked(
                    request_item=request_item,
                    collection_key=collection_key,
                )

        items = upload_service._load_upload_requests_unlocked()
        items.append(request_item)
        upload_service._save_upload_requests_unlocked(items)

    return {"auto_approve": auto_approve, "request": _view_request_item(request_item)}


@router.post("/upload-requests/{request_id}/approve")
def approve_upload_request(request_id: str, action: UploadRequestApproveAction) -> dict[str, object]:
    return {
        "request": upload_service.approve_upload_request(
            request_id=request_id,
            code=action.code,
            collection=action.collection,
        )
    }


@router.post("/upload-requests/{request_id}/reject")
def reject_upload_request(request_id: str, action: UploadRequestRejectAction) -> dict[str, object]:
    return {
        "request": upload_service.reject_upload_request(
            request_id=request_id,
            code=action.code,
            reason=action.reason,
            reason_code=action.reason_code,
            decision_note=action.decision_note,
        )
    }
