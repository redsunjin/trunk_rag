from __future__ import annotations

from pathlib import Path

from api import routes_upload


def test_admin_auth_success_and_failure(client, monkeypatch):
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "123456")

    success = client.post("/admin/auth", json={"code": "123456"})
    assert success.status_code == 200
    assert success.json() == {"ok": True}

    failure = client.post("/admin/auth", json={"code": "wrong"})
    assert failure.status_code == 401


def _sample_markdown() -> str:
    return "## 테스트 섹션\n이 문서는 업로드 요청 테스트를 위한 충분한 길이의 본문을 포함합니다."


def test_upload_request_create_pending_and_list(client, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        routes_upload.upload_service,
        "upload_request_store_path",
        lambda: tmp_path / "upload_requests.json",
    )
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
    request_id = body["request"]["id"]

    listing = client.get("/upload-requests", params={"status": "pending"})
    assert listing.status_code == 200
    listed = listing.json()
    assert listed["counts"]["pending"] == 1
    assert any(item["id"] == request_id for item in listed["requests"])


def test_upload_request_approve_and_reject(client, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        routes_upload.upload_service,
        "upload_request_store_path",
        lambda: tmp_path / "upload_requests.json",
    )
    monkeypatch.setenv("DOC_RAG_AUTO_APPROVE", "0")
    monkeypatch.setenv("DOC_RAG_ADMIN_CODE", "admin999")
    monkeypatch.setattr(
        routes_upload.index_service,
        "index_documents_for_collection",
        lambda docs, collection_key, reset: {
            "chunks_added": len(docs),
            "vectors": 99,
            "cap": {"soft_cap": 30000, "hard_cap": 50000},
            "collection": "mock_collection",
            "collection_key": collection_key,
        },
    )

    first = client.post(
        "/upload-requests",
        json={
            "source_name": "approve_target.md",
            "collection": "all",
            "content": _sample_markdown(),
        },
    )
    assert first.status_code == 200
    first_id = first.json()["request"]["id"]

    approved = client.post(f"/upload-requests/{first_id}/approve", json={"code": "admin999"})
    assert approved.status_code == 200
    assert approved.json()["request"]["status"] == "approved"

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
        json={"code": "admin999", "reason": "형식 미흡"},
    )
    assert rejected.status_code == 200
    assert rejected.json()["request"]["status"] == "rejected"
    assert rejected.json()["request"]["rejected_reason"] == "형식 미흡"


def test_upload_request_filter_by_rejected_reason(client, monkeypatch, tmp_path: Path):
    monkeypatch.setattr(
        routes_upload.upload_service,
        "upload_request_store_path",
        lambda: tmp_path / "upload_requests.json",
    )
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
        json={"code": "admin999", "reason": "형식 미흡"},
    )
    assert rejected_first.status_code == 200
    rejected_second = client.post(
        f"/upload-requests/{second_id}/reject",
        json={"code": "admin999", "reason": "중복 문서"},
    )
    assert rejected_second.status_code == 200

    listing = client.get("/upload-requests", params={"status": "rejected", "reason": "형식"})
    assert listing.status_code == 200
    body = listing.json()
    assert body["counts"]["rejected"] == 2
    assert len(body["requests"]) == 1
    assert body["requests"][0]["id"] == first_id
    assert body["requests"][0]["rejected_reason"] == "형식 미흡"
