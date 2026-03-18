from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


ROOT_DIR = Path(__file__).resolve().parents[2]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: int = 45) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(f"{base_url}/health", timeout=1) as response:
                if response.status == 200:
                    return
        except Exception:
            time.sleep(0.25)
    raise RuntimeError(f"Timed out waiting for server: {base_url}")


@pytest.fixture(scope="session")
def live_server_url():
    port = _find_free_port()
    base_url = f"http://127.0.0.1:{port}"
    process = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app_api:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(port),
        ],
        cwd=ROOT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )

    try:
        _wait_for_server(base_url)
        yield base_url
    finally:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()


@pytest.mark.e2e
def test_intro_app_flow(page: Page, live_server_url: str):
    page.goto(f"{live_server_url}/intro", wait_until="domcontentloaded")
    expect(page.locator("#statusIndicator .status-text")).to_have_text(re.compile(r"Online|Ready"), timeout=15000)
    expect(page.locator("#statusMsg")).to_contain_text("llm=", timeout=15000)

    page.click("#userStartBtn")
    expect(page).to_have_url(re.compile(r".*/app$"), timeout=10000)
    expect(page.locator("#runtimeSummary")).to_contain_text("기본 질의 설정", timeout=10000)
    expect(page.locator("#advancedSettings")).to_be_hidden()
    expect(page.locator("#uploadMetadataFields")).to_be_hidden()
    expect(page.locator("#uploadDefaultsSummary")).to_contain_text("source=auto")
    page.click("#advancedSettingsToggle")
    expect(page.locator("#advancedSettings")).to_be_visible()
    page.click("#advancedSettingsToggle")
    expect(page.locator("#advancedSettings")).to_be_hidden()
    page.click("#uploadMetadataToggle")
    expect(page.locator("#uploadMetadataFields")).to_be_visible()
    page.click("#uploadMetadataToggle")
    expect(page.locator("#uploadMetadataFields")).to_be_hidden()

    first_doc_button = page.locator(".doc-item-btn").first
    expect(first_doc_button).to_be_visible(timeout=10000)
    first_doc_name = first_doc_button.locator(".doc-name").inner_text().strip()
    first_doc_button.click()
    expect(page.locator("#docTitle")).to_contain_text(first_doc_name)

    expect(page.locator("#collection option[value='fr']")).to_have_count(1, timeout=10000)
    expect(page.locator("#collection2 option[value='ge']")).to_have_count(1, timeout=10000)
    page.select_option("#collection", "fr")
    page.select_option("#collection2", "ge")
    expect(page.locator("#uploadDefaultsSummary")).to_contain_text("country=france")
    expect(page.locator("#uploadDefaultsSummary")).to_contain_text("doc_type=country")

    def health_success(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "status": "ok",
                    "collection_key": "all",
                    "collection": "w2_007_header_rag",
                    "persist_dir": "mock",
                    "vectors": 37,
                    "auto_approve": False,
                    "pending_requests": 0,
                    "chunking_mode": "char",
                    "query_timeout_seconds": 15,
                    "max_context_chars": 1500,
                    "default_llm_provider": "ollama",
                    "default_llm_model": "qwen3:4b",
                    "default_llm_base_url": "http://localhost:11434",
                }
            ),
        )

    page.route("**/health", health_success)
    page.click("#healthBtn")
    expect(page.locator("#statusMsg")).to_contain_text("vectors=37")

    query_payload: dict[str, object] = {}

    def query_success(route):
        query_payload["body"] = route.request.post_data_json
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "answer": "모킹된 질의 응답",
                    "provider": "ollama",
                    "model": "qwen3:4b",
                }
            ),
        )

    page.route("**/query", query_success)
    page.fill("#userInput", "정상 응답 테스트")
    page.click("#sendBtn")
    expect(page.locator(".chat-message.bot").last).to_have_text("모킹된 질의 응답", timeout=10000)
    assert query_payload["body"]["collection"] == "fr"
    assert query_payload["body"]["collections"] == ["fr", "ge"]
    page.unroute("**/query", query_success)

    def query_failure(route):
        route.fulfill(
            status=504,
            content_type="application/json",
            body=json.dumps(
                {
                    "code": "LLM_TIMEOUT",
                    "message": "LLM 응답 시간이 제한(15초)을 초과했습니다.",
                    "hint": "모델 상태를 확인하거나 더 짧은 질문으로 다시 시도하세요.",
                    "request_id": "req-e2e-timeout",
                    "detail": "LLM 응답 시간이 제한(15초)을 초과했습니다.",
                }
            ),
            headers={"X-Request-ID": "req-e2e-timeout"},
        )

    page.route("**/query", query_failure)
    page.fill("#userInput", "오류 응답 테스트")
    page.click("#sendBtn")
    expect(page.locator(".chat-message.bot").last).to_contain_text("LLM 응답 시간이 제한")
    expect(page.locator(".chat-message.bot").last).to_contain_text("hint:")
    expect(page.locator(".chat-message.bot").last).to_contain_text("request_id:")
    page.unroute("**/query", query_failure)

    def reindex_success(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "docs": 5,
                    "chunks": 37,
                    "vectors": 99,
                    "persist_dir": "mock",
                    "collection": "w2_007_header_rag",
                    "validation": {
                        "summary_text": "total=5, usable=5, rejected=0, warnings=0, usable_ratio=100.00%",
                    },
                }
            ),
        )

    page.route("**/reindex", reindex_success)
    page.click("#reindexBtn")
    expect(page.locator(".chat-message.bot").last).to_contain_text("재인덱싱 완료")
    expect(page.locator(".chat-message.bot").last).to_contain_text("vectors=99")
    expect(page.locator(".chat-message.bot").last).to_contain_text("usable_ratio=100.00%")
    page.unroute("**/reindex", reindex_success)

    upload_payload: dict[str, object] = {}

    def upload_request_success(route):
        upload_payload["body"] = route.request.post_data_json
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "auto_approve": False,
                    "request": {
                        "id": "req-upload-1",
                        "status": "pending",
                    },
                }
            ),
        )

    page.route("**/upload-requests", upload_request_success)
    page.fill("#uploadContent", "## 업로드 테스트\n충분한 본문 길이를 가진 테스트 문장입니다.")
    page.click("#uploadBtn")
    expect(page.locator("#uploadMsg")).to_contain_text("req-upload-1")
    expect(page.locator("#uploadMsg")).to_contain_text("pending")
    assert upload_payload["body"]["source_name"] is None
    assert upload_payload["body"]["country"] is None
    assert upload_payload["body"]["doc_type"] is None
    page.unroute("**/upload-requests", upload_request_success)

    def upload_request_rejected(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "auto_approve": True,
                    "request": {
                        "id": "req-upload-2",
                        "status": "rejected",
                        "source_name": "bad_upload.md",
                        "rejected_reason": "auto-approve enabled but validation failed",
                        "validation": {
                            "reasons": ["헤더 누락"],
                        },
                    },
                }
            ),
        )

    page.route("**/upload-requests", upload_request_rejected)
    page.fill("#uploadContent", "본문만 있고 헤더가 없는 문장")
    page.click("#uploadBtn")
    expect(page.locator("#uploadMsg")).to_contain_text("req-upload-2")
    expect(page.locator(".chat-message.bot").last).to_contain_text("반려되었습니다")
    expect(page.locator(".chat-message.bot").last).to_contain_text("validation failed")
    page.unroute("**/upload-requests", upload_request_rejected)
    page.unroute("**/health", health_success)


@pytest.mark.e2e
def test_admin_search_filters_flow(page: Page, live_server_url: str):
    request_queries: list[dict[str, list[str]]] = []

    def collections_handler(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "default_collection_key": "all",
                    "auto_approve": False,
                    "collections": [
                        {
                            "key": "all",
                            "label": "전체 (기본)",
                            "name": "w2_007_header_rag",
                            "vectors": 10,
                            "soft_usage_ratio": 0.0,
                            "hard_usage_ratio": 0.0,
                            "soft_exceeded": False,
                            "hard_exceeded": False,
                        }
                    ],
                }
            ),
        )

    def upload_requests_handler(route):
        parsed = urllib.parse.urlparse(route.request.url)
        query = urllib.parse.parse_qs(parsed.query)
        request_queries.append(query)
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "auto_approve": False,
                    "counts": {"pending": 1, "approved": 0, "rejected": 0},
                    "requests": [
                        {
                            "id": "req-admin-1",
                            "source_name": "sample_upload.md",
                            "collection_key": "fr",
                            "doc_key": "fr",
                            "request_type": "update",
                            "change_summary": "기존 프랑스 문서 갱신",
                            "status": "pending",
                            "usable": True,
                            "created_at": "2026-02-26T00:00:00+00:00",
                            "updated_at": "2026-02-26T00:01:00+00:00",
                            "content_preview": "## 갱신 문서\n핵심 문단 보강",
                            "validation": {"reasons": [], "warnings": ["기존 문서 갱신"]},
                            "active_doc_exists": True,
                            "active_doc": {
                                "exists": True,
                                "origin": "seed",
                                "source_name": "fr.md",
                                "change_summary": "",
                                "preview": "## 프랑스 과학 문서",
                            },
                        }
                    ],
                }
            ),
        )

    page.route("**/collections", collections_handler)
    page.route("**/upload-requests**", upload_requests_handler)

    page.goto(f"{live_server_url}/admin", wait_until="domcontentloaded")
    expect(page.locator("#statusFilter")).to_have_value("pending", timeout=10000)
    expect(page.locator("#requestMsg")).to_contain_text("pending=1", timeout=10000)
    expect(page.locator("#requestTableWrap")).to_contain_text("update")
    expect(page.locator("#requestTableWrap")).to_contain_text("기존 프랑스 문서 갱신")
    expect(page.locator("#requestDetailWrap")).to_contain_text("active_doc_exists: 있음")
    expect(page.locator("#requestDetailWrap")).to_contain_text("기존 프랑스 문서 갱신")
    expect(page.locator("#requestDetailWrap")).to_contain_text("프랑스 과학 문서")

    page.fill("#reasonFilter", "형식")
    page.fill("#searchFilter", "sample")
    page.press("#searchFilter", "Enter")
    page.wait_for_timeout(300)

    assert any(
        query.get("reason") == ["형식"] and query.get("q") == ["sample"]
        for query in request_queries
    )
    assert any(query.get("status") == ["pending"] for query in request_queries)
