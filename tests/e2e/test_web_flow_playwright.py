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
    expect(page.locator("#statusIndicator .status-text")).to_have_text("Online", timeout=15000)

    page.click("#userStartBtn")
    expect(page).to_have_url(re.compile(r".*/app$"), timeout=10000)

    first_doc_button = page.locator(".doc-item-btn").first
    expect(first_doc_button).to_be_visible(timeout=10000)
    first_doc_name = first_doc_button.locator(".doc-name").inner_text().strip()
    first_doc_button.click()
    expect(page.locator("#docTitle")).to_contain_text(first_doc_name)

    expect(page.locator("#collection option[value='fr']")).to_have_count(1, timeout=10000)
    expect(page.locator("#collection2 option[value='ge']")).to_have_count(1, timeout=10000)
    page.select_option("#collection", "fr")
    page.select_option("#collection2", "ge")

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
    expect(page.locator("#statusMsg")).to_contain_text("reindex 완료")
    expect(page.locator("#statusMsg")).to_contain_text("vectors=99")
    expect(page.locator("#statusMsg")).to_contain_text("usable_ratio=100.00%")
    page.unroute("**/reindex", reindex_success)

    def upload_request_success(route):
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
    page.unroute("**/upload-requests", upload_request_success)


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
                    "counts": {"pending": 0, "approved": 0, "rejected": 1},
                    "requests": [
                        {
                            "id": "req-admin-1",
                            "source_name": "sample_upload.md",
                            "collection_key": "fr",
                            "status": "rejected",
                            "usable": False,
                            "created_at": "2026-02-26T00:00:00+00:00",
                            "updated_at": "2026-02-26T00:01:00+00:00",
                            "rejected_reason": "형식 미흡",
                            "validation": {"reasons": ["헤더 누락"]},
                        }
                    ],
                }
            ),
        )

    page.route("**/collections", collections_handler)
    page.route("**/upload-requests**", upload_requests_handler)

    page.goto(f"{live_server_url}/admin", wait_until="domcontentloaded")
    expect(page.locator("#requestMsg")).to_contain_text("rejected=1", timeout=10000)
    expect(page.locator("#requestTableWrap")).to_contain_text("형식 미흡")
    expect(page.locator("#requestTableWrap")).to_contain_text("헤더 누락")

    page.fill("#reasonFilter", "형식")
    page.fill("#searchFilter", "sample")
    page.press("#searchFilter", "Enter")
    page.wait_for_timeout(300)

    assert any(
        query.get("reason") == ["형식"] and query.get("q") == ["sample"]
        for query in request_queries
    )
