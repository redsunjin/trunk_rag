from __future__ import annotations

import json
import re
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

import pytest
from playwright.sync_api import Page, expect


ROOT_DIR = Path(__file__).resolve().parents[2]


def _find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_server(base_url: str, timeout_seconds: int = 20) -> None:
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

    page.click("#startBtn")
    expect(page).to_have_url(re.compile(r".*/app$"), timeout=10000)

    first_doc_button = page.locator(".doc-item-btn").first
    expect(first_doc_button).to_be_visible(timeout=10000)
    first_doc_name = first_doc_button.locator(".doc-name").inner_text().strip()
    first_doc_button.click()
    expect(page.locator("#docTitle")).to_contain_text(first_doc_name)

    def query_success(route):
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
                }
            ),
        )

    page.route("**/reindex", reindex_success)
    page.click("#reindexBtn")
    expect(page.locator("#statusMsg")).to_contain_text("reindex 완료: vectors=99")
    page.unroute("**/reindex", reindex_success)
