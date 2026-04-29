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
    def ops_baseline_latest(route):
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "status": "ok",
                    "ready": True,
                    "generated_at": "2026-04-01T00:00:00Z",
                    "summary": {
                        "cases": 3,
                        "passed": 3,
                        "pass_rate": 1.0,
                        "avg_latency_ms": 1000.0,
                        "p95_latency_ms": 1500.0,
                        "avg_weighted_score": 0.96,
                    },
                    "diagnostics": [],
                    "missing_keys": [],
                    "collections_ready": True,
                    "runtime_ready": True,
                }
            ),
        )

    page.route("**/ops-baseline/latest", ops_baseline_latest)
    page.goto(f"{live_server_url}/intro", wait_until="domcontentloaded")
    expect(page.locator("#statusIndicator .status-text")).to_have_text(re.compile(r"Online|Ready"), timeout=15000)
    expect(page.locator("#statusMsg")).to_contain_text("문서", timeout=15000)
    expect(page.locator("#runtimeProfileMsg")).to_contain_text("런타임:", timeout=15000)
    expect(page.locator("#releaseGuideMsg")).to_contain_text("상태 요약", timeout=15000)
    expect(page.locator("#releaseStatusBadge")).to_have_text(
        re.compile(r"ready|needs_reindex|runtime_warning|needs_verified_runtime"),
        timeout=15000,
    )
    expect(page.locator("#releaseStepsList")).to_contain_text("run_doc_rag.bat", timeout=15000)
    expect(page.locator("#recoveryHintMsg")).to_contain_text(re.compile(r"상태|질의|Reindex|운영"), timeout=15000)
    expect(page.locator("#opsBaselineMsg")).to_contain_text("pass_rate=1")

    page.click("#userStartBtn")
    expect(page).to_have_url(re.compile(r".*/app$"), timeout=10000)
    expect(page.locator(".app-overview-card")).to_contain_text("로컬 RAG 작업 공간")
    expect(page.locator(".app-overview-card")).to_contain_text("유럽 과학사 샘플 데모")
    expect(page.locator(".sidebar-section").filter(has_text="RAG Documents")).to_contain_text("샘플 데모")
    expect(page.locator(".sidebar-section").filter(has_text="문서 추가/갱신 요청")).to_contain_text("문서 반영 방식")
    expect(page.locator("#appOpsBaselineMsg")).to_contain_text("최근 ops-baseline")
    expect(page.locator("#appRecoverySteps")).to_contain_text("run_doc_rag.bat", timeout=10000)
    expect(page.locator(".sidebar-header .brand-mark")).to_have_count(0)
    expect(page.locator(".sidebar-header .settings-icon")).to_be_visible()
    expect(page.locator(".sidebar-header")).to_contain_text("Settings")
    expect(page.locator("#runtimeSummary")).to_contain_text("기본 질의 설정", timeout=10000)
    expect(page.locator("#runtimeSummary")).not_to_contain_text("localhost")
    expect(page.locator("#runtimeProfileMsg")).not_to_contain_text("budget_summary")
    expect(page.locator("#advancedSettings")).to_be_hidden()
    expect(page.locator("input[name='qualityMode'][value='balanced']")).to_be_checked()
    expect(page.locator("#qualityModeHint")).to_contain_text("e2b")
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
                    "query_timeout_seconds": 30,
                    "max_context_chars": 1500,
                    "default_llm_provider": "ollama",
                    "default_llm_model": "llama3.1:8b",
                    "default_llm_base_url": "http://localhost:11434",
                    "runtime_profile_status": "verified",
                    "runtime_profile_scope": "local",
                    "runtime_profile_message": "현재 Ollama 런타임 프로파일은 로컬 ops-baseline 실측에서 검증됐습니다.",
                    "runtime_profile_recommendation": "`DOC_RAG_QUERY_TIMEOUT_SECONDS=30` 이상을 유지하세요.",
                    "runtime_query_budget_profile": "verified_local_single",
                    "runtime_query_budget_summary": "profile=verified_local_single | k=3",
                    "embedding_fingerprint_status": "ready",
                    "embedding_fingerprint_message": "ok",
                    "release_web_headline": "run_doc_rag.bat 기준 기본 경로 확인",
                    "release_web_steps": ["run_doc_rag.bat 실행", "/intro 확인", "/app 진입"],
                }
            ),
        )

    page.route("**/health", health_success)
    page.click("#healthBtn")
    expect(page.locator("#statusMsg")).to_contain_text("vectors=37")
    expect(page.locator("#runtimeProfileMsg")).to_contain_text("verified")
    expect(page.locator("#appOverviewRuntime")).to_contain_text("문서 벡터=37")
    expect(page.locator("#appRecoverySteps")).to_contain_text("/intro 확인")

    semantic_payload: dict[str, object] = {}
    query_payload: dict[str, object] = {}

    def semantic_success(route):
        semantic_payload["body"] = route.request.post_data_json
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "query": "정상 응답 테스트",
                    "results": [
                        {
                            "rank": 1,
                            "source": "fr_doc.md",
                            "h2": "프랑스",
                            "collection_key": "fr",
                            "snippet": "프랑스 과학 교육 제도에 대한 빠른 검색 근거입니다.",
                        },
                        {
                            "rank": 2,
                            "source": "ge_doc.md",
                            "h2": "독일",
                            "collection_key": "ge",
                            "snippet": "독일 연구 대학에 대한 빠른 검색 근거입니다.",
                        },
                    ],
                    "meta": {
                        "request_id": "req-semantic-e2e-1",
                        "query_profile": "generic",
                        "collections": ["fr", "ge"],
                        "route_reason": "explicit_multi",
                        "search_mode": "semantic_fallback",
                        "retrieval_strategy": "mmr+light_hybrid",
                        "stage_timings": {"semantic_retrieval_ms": 25.0},
                        "context": {"docs_total": 2, "context_chars": 180},
                    },
                }
            ),
        )

    def query_success(route):
        query_payload["body"] = route.request.post_data_json
        request_body = query_payload["body"]
        is_quality = request_body.get("quality_mode") == "quality"
        graph_lite_meta = {
            "enabled": is_quality,
            "mode": "quality" if is_quality else "balanced",
            "status": "hit" if is_quality else "disabled",
            "fallback_used": False,
            "fallback_reason": None,
            "relation_count": 2 if is_quality else 0,
            "context_added": is_quality,
        }
        route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps(
                {
                    "answer": "모킹된 정밀 질의 응답" if is_quality else "모킹된 질의 응답",
                    "provider": "ollama",
                    "model": "qwen3.5:9b-nvfp4" if is_quality else "gemma4:e2b",
                    "meta": {
                        "request_id": "req-e2e-1",
                        "collections": ["fr", "ge"],
                        "route_reason": "explicit_multi",
                        "budget_profile": "verified_local_multi" if not is_quality else "quality_candidate",
                        "quality_mode": "quality" if is_quality else "balanced",
                        "quality_stage": "quality" if is_quality else "fast",
                        "support_level": "supported",
                        "support_reason": "multiple_context_segments",
                        "citations": ["fr_doc.md > 프랑스", "ge_doc.md > 독일"],
                        "stage_timings": {"resolve_route_ms": 1.2},
                        "context": {
                            "docs_total": 2,
                            "context_chars": 240,
                            "graph_lite": graph_lite_meta,
                        },
                        "invoke": {"invoke_ms": 420.5, "status": "ok"},
                        "sources": [
                            {"source": "fr_doc.md", "h2": "프랑스", "collection_key": "fr"},
                            {"source": "ge_doc.md", "h2": "독일", "collection_key": "ge"},
                        ],
                    },
                }
            ),
        )

    page.route("**/semantic-search", semantic_success)
    page.route("**/query", query_success)
    page.fill("#userInput", "정상 응답 테스트")
    page.click("#sendBtn")
    expect(page.locator(".semantic-result-list").last).to_contain_text("fr_doc.md", timeout=10000)
    expect(page.locator(".semantic-result-list").last).to_contain_text("프랑스 과학 교육")
    expect(page.locator(".chat-message.bot").last).to_contain_text("모킹된 질의 응답", timeout=10000)
    expect(page.locator(".chat-message.bot").last).to_contain_text("근거 수준=supported")
    expect(page.locator(".chat-message.bot").last).to_contain_text("fr_doc.md > 프랑스")
    expect(page.locator(".chat-message.bot").last).to_contain_text("graph-lite=disabled")
    page.locator(".chat-message.bot").last.locator("summary").click()
    expect(page.locator(".chat-message.bot").last).to_contain_text("request_id=req-e2e-1")
    expect(page.locator(".chat-message.bot").last).to_contain_text("fr_doc.md")
    assert semantic_payload["body"]["collection"] == "fr"
    assert semantic_payload["body"]["collections"] == ["fr", "ge"]
    assert semantic_payload["body"]["max_results"] == 3
    assert semantic_payload["body"]["quality_mode"] == "balanced"
    assert query_payload["body"]["collection"] == "fr"
    assert query_payload["body"]["collections"] == ["fr", "ge"]
    assert query_payload["body"]["timeout_seconds"] == 60
    assert query_payload["body"]["debug"] is True
    assert query_payload["body"]["quality_mode"] == "balanced"
    assert query_payload["body"]["quality_stage"] == "fast"
    assert query_payload["body"]["llm_provider"] == "ollama"
    assert query_payload["body"]["llm_model"] == "gemma4:e2b"

    page.locator(".segmented-option").filter(has_text="Quality").click()
    page.fill("#userInput", "정밀 관계 응답 테스트")
    page.click("#sendBtn")
    expect(page.locator(".chat-message.bot").last).to_contain_text("모킹된 정밀 질의 응답", timeout=10000)
    expect(page.locator(".chat-message.bot").last).to_contain_text("graph-lite=hit")
    expect(page.locator(".chat-message.bot").last).to_contain_text("relations=2")
    page.locator(".chat-message.bot").last.locator("summary").click()
    expect(page.locator(".chat-message.bot").last).to_contain_text("context=added")
    assert query_payload["body"]["quality_mode"] == "quality"
    assert query_payload["body"]["quality_stage"] == "quality"
    assert query_payload["body"]["timeout_seconds"] == 120

    page.unroute("**/query", query_success)
    page.unroute("**/semantic-search", semantic_success)

    def query_failure(route):
        route.fulfill(
            status=504,
            content_type="application/json",
            body=json.dumps(
                {
                    "code": "LLM_TIMEOUT",
                    "message": "LLM 응답 시간이 제한(30초)을 초과했습니다.",
                    "hint": "모델 상태를 확인하거나 더 짧은 질문으로 다시 시도하세요.",
                    "request_id": "req-e2e-timeout",
                    "detail": "LLM 응답 시간이 제한(30초)을 초과했습니다.",
                }
            ),
            headers={"X-Request-ID": "req-e2e-timeout"},
        )

    page.route("**/semantic-search", semantic_success)
    page.route("**/query", query_failure)
    page.fill("#userInput", "오류 응답 테스트")
    page.click("#sendBtn")
    expect(page.locator(".semantic-result-list").last).to_contain_text("fr_doc.md", timeout=10000)
    expect(page.locator(".chat-message.bot").last).to_contain_text("LLM 응답 시간이 제한")
    expect(page.locator(".chat-message.bot").last).to_contain_text("hint:")
    expect(page.locator(".chat-message.bot").last).to_contain_text("request_id:")
    expect(page.locator(".chat-message.bot").last).to_contain_text("빠른 시맨틱 검색 결과")
    page.unroute("**/query", query_failure)
    page.unroute("**/semantic-search", semantic_success)

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
    page.unroute("**/ops-baseline/latest", ops_baseline_latest)


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
