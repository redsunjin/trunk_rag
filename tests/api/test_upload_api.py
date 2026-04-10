from __future__ import annotations

from pathlib import Path

from core.settings import UPLOAD_REQUEST_LOCK
from api import routes_upload
from services import index_service


def test_admin_auth_success_and_failure(client, monkeypatch):
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "123456")

    success = client.post("/admin/auth", json={"code": "123456"})
    assert success.status_code == 200
    assert success.json() == {"ok": True}

    failure = client.post("/admin/auth", json={"code": "wrong"})
    assert failure.status_code == 401


def _sample_markdown() -> str:
    return "## 테스트 섹션\n이 문서는 업로드 요청 테스트를 위한 충분한 길이의 본문을 포함합니다."


def _patch_upload_storage(monkeypatch, tmp_path: Path) -> None:
    def managed_dir() -> Path:
        path = tmp_path / "managed_docs"
        path.mkdir(parents=True, exist_ok=True)
        return path

    monkeypatch.setattr(
        routes_upload.upload_service,
        "upload_request_store_path",
        lambda: tmp_path / "upload_requests.json",
    )
    monkeypatch.setattr(
        routes_upload.upload_service,
        "managed_doc_store_dir",
        managed_dir,
    )


def test_upload_request_create_pending_and_list(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")

    create = client.post(
        "/upload-requests",
        json={
            "source_name": "sample_upload.md",
            "collection": "fr",
            "country": "france",
            "doc_type": "country",
            "content": _sample_markdown(),
        },
    )
    assert create.status_code == 200
    body = create.json()
    assert body["auto_approve"] is False
    assert body["request"]["status"] == "pending"
    assert body["request"]["request_type"] == "create"
    assert body["request"]["doc_key"] == "sample_upload"
    assert body["request"]["active_doc_exists"] is False
    assert "테스트 섹션" in body["request"]["content_preview"]
    request_id = body["request"]["id"]

    listing = client.get("/upload-requests", params={"status": "pending"})
    assert listing.status_code == 200
    listed = listing.json()
    assert listed["counts"]["pending"] == 1
    assert any(item["id"] == request_id for item in listed["requests"])


def test_upload_request_update_includes_active_doc_summary(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")

    create = client.post(
        "/upload-requests",
        json={
            "source_name": "fr_refresh.md",
            "collection": "fr",
            "request_type": "update",
            "doc_key": "fr",
            "change_summary": "핵심 문단 보강",
            "content": _sample_markdown(),
        },
    )
    assert create.status_code == 200
    body = create.json()["request"]
    assert body["status"] == "pending"
    assert body["request_type"] == "update"
    assert body["active_doc_exists"] is True
    assert body["active_doc"]["origin"] == "seed"
    assert body["active_doc"]["source_name"].endswith(".md")
    assert body["active_doc"]["preview"]

    detail = client.get(f"/upload-requests/{body['id']}")
    assert detail.status_code == 200
    detail_body = detail.json()["request"]
    assert detail_body["active_doc_exists"] is True
    assert detail_body["active_doc"]["origin"] == "seed"
    assert detail_body["content_preview"]


def test_upload_request_uses_collection_defaults_when_optional_fields_are_omitted(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")

    create = client.post(
        "/upload-requests",
        json={
            "collection": "ge",
            "content": _sample_markdown(),
        },
    )
    assert create.status_code == 200
    body = create.json()
    request = body["request"]
    assert request["status"] == "pending"
    assert request["source_name"].startswith("upload_")
    assert request["source_name"].endswith(".md")
    assert request["doc_key"].startswith("upload_")
    assert request["request_type"] == "create"
    assert request["metadata"]["country"] == "germany"
    assert request["metadata"]["doc_type"] == "country"


def test_upload_request_auto_approve_skips_update_requests(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "1")

    create = client.post(
        "/upload-requests",
        json={
            "source_name": "fr_refresh.md",
            "collection": "fr",
            "doc_key": "fr",
            "content": _sample_markdown(),
        },
    )
    assert create.status_code == 200
    body = create.json()
    assert body["auto_approve"] is False
    assert body["request"]["request_type"] == "update"
    assert body["request"]["status"] == "pending"


def test_upload_request_rejects_invalid_explicit_request_type(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")

    create = client.post(
        "/upload-requests",
        json={
            "source_name": "new_doc.md",
            "collection": "fr",
            "request_type": "update",
            "doc_key": "new_doc",
            "content": _sample_markdown(),
        },
    )
    assert create.status_code == 422
    assert "doc_key not found for update" in create.json()["detail"]


def test_upload_request_approve_persists_managed_doc_and_reject(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "admin999")
    monkeypatch.setattr(
        index_service,
        "reindex",
        lambda reset=True, collection_key="all": {
            "docs": 1,
            "docs_total": 1,
            "chunks": 1,
            "vectors": 99,
            "cap": {"soft_cap": 30000, "hard_cap": 50000},
            "collection": "mock_collection",
            "collection_key": collection_key,
            "chunking": {"mode": "char", "chunk_size": 800, "chunk_overlap": 120},
            "validation": {"summary_text": "ok"},
        },
    )

    first = client.post(
        "/upload-requests",
        json={
            "source_name": "approve_target.md",
            "collection": "fr",
            "change_summary": "초안 등록",
            "content": _sample_markdown(),
        },
    )
    assert first.status_code == 200
    first_id = first.json()["request"]["id"]

    approved = client.post(f"/upload-requests/{first_id}/approve", json={"code": "admin999"})
    assert approved.status_code == 200
    approved_body = approved.json()["request"]
    assert approved_body["status"] == "approved"
    assert approved_body["request_type"] == "create"
    assert approved_body["managed_doc"]["active"] is True
    assert approved_body["managed_doc"]["doc_key"] == "approve_target"
    assert approved_body["managed_doc"]["change_summary"] == "초안 등록"
    assert approved_body["ingest"]["mode"] == "reindex"
    assert set(approved_body["ingest"]["collections"].keys()) == {"all", "fr"}

    docs = client.get("/rag-docs")
    assert docs.status_code == 200
    listed_docs = docs.json()["docs"]
    managed_doc = next((item for item in listed_docs if item["name"] == "approve_target.md"), None)
    assert managed_doc is not None
    assert managed_doc["origin"] == "managed"
    assert managed_doc["doc_key"] == "approve_target"
    assert managed_doc["collection_key"] == "fr"

    doc_detail = client.get("/rag-docs/approve_target.md")
    assert doc_detail.status_code == 200
    assert doc_detail.json()["name"] == "approve_target.md"
    assert "테스트 섹션" in doc_detail.json()["content"]

    second = client.post(
        "/upload-requests",
        json={
            "source_name": "reject_target.md",
            "collection": "all",
            "content": _sample_markdown(),
        },
    )
    assert second.status_code == 200
    second_id = second.json()["request"]["id"]

    rejected = client.post(
        f"/upload-requests/{second_id}/reject",
        json={"code": "admin999", "reason_code": "FORMAT", "reason": "형식 미흡"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["request"]["status"] == "rejected"
    assert rejected.json()["request"]["rejected_reason"] == "형식 미흡"
    assert rejected.json()["request"]["rejected_reason_code"] == "FORMAT"
    assert rejected.json()["request"]["decision_note"] == "형식 미흡"
    assert rejected.json()["request"]["rejected_reason_note"] == "형식 미흡"

    with UPLOAD_REQUEST_LOCK:
        managed_items = routes_upload.upload_service._load_managed_docs_unlocked()
    assert len(managed_items) == 1


def test_upload_request_filter_by_rejected_reason(client, monkeypatch, tmp_path: Path):
    _patch_upload_storage(monkeypatch, tmp_path)
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "admin999")

    first = client.post(
        "/upload-requests",
        json={
            "source_name": "reject_target_1.md",
            "collection": "all",
            "content": _sample_markdown(),
        },
    )
    assert first.status_code == 200
    first_id = first.json()["request"]["id"]

    second = client.post(
        "/upload-requests",
        json={
            "source_name": "reject_target_2.md",
            "collection": "all",
            "content": _sample_markdown(),
        },
    )
    assert second.status_code == 200
    second_id = second.json()["request"]["id"]

    rejected_first = client.post(
        f"/upload-requests/{first_id}/reject",
        json={"code": "admin999", "reason_code": "FORMAT", "reason": "형식 미흡"},
    )
    assert rejected_first.status_code == 200
    rejected_second = client.post(
        f"/upload-requests/{second_id}/reject",
        json={"code": "admin999", "reason_code": "DUPLICATE", "reason": "중복 문서"},
    )
    assert rejected_second.status_code == 200

    listing = client.get("/upload-requests", params={"status": "rejected", "reason": "FORMAT"})
    assert listing.status_code == 200
    body = listing.json()
    assert body["counts"]["rejected"] == 2
    assert len(body["requests"]) == 1
    assert body["requests"][0]["id"] == first_id
    assert body["requests"][0]["rejected_reason"] == "형식 미흡"
    assert body["requests"][0]["rejected_reason_code"] == "FORMAT"
