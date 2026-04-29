from __future__ import annotations

import argparse
import json
import tempfile
import time
from pathlib import Path
from typing import Any

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright


DEFAULT_CHROME_EXECUTABLE = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
DEFAULT_SERVER_URL = "http://127.0.0.1:8000"
DEFAULT_BALANCED_QUESTION = "기본 문서가 무엇인지 한 문장으로 설명해줘"
DEFAULT_QUALITY_QUESTION = "영국과 이탈리아 문서에서 과학 발전의 차이를 관계 중심으로 비교해줘"
EXTENSION_NAME = "Trunk RAG Companion"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a local loaded-extension smoke for browser_companion/.",
    )
    parser.add_argument("--extension-dir", default="browser_companion")
    parser.add_argument("--server-url", default=DEFAULT_SERVER_URL)
    parser.add_argument("--chrome-executable", default=DEFAULT_CHROME_EXECUTABLE)
    parser.add_argument("--balanced-question", default=DEFAULT_BALANCED_QUESTION)
    parser.add_argument("--quality-question", default=DEFAULT_QUALITY_QUESTION)
    parser.add_argument("--skip-quality", action="store_true")
    parser.add_argument("--skip-upload", action="store_true")
    parser.add_argument("--output-json", default="")
    return parser.parse_args()


def wait_for_result(page: Any, timeout: int) -> str:
    page.wait_for_function(
        """() => {
            const el = document.querySelector("#resultPanel");
            return el && el.innerText && !el.innerText.includes("질의 중...");
        }""",
        timeout=timeout,
    )
    return page.locator("#resultPanel").inner_text()


def run_query(page: Any, question: str, mode: str, timeout: int) -> dict[str, Any]:
    page.fill("#questionInput", question)
    page.select_option("#qualityMode", mode)
    started = time.time()
    page.click("#askBtn")
    result_text = wait_for_result(page, timeout=timeout)
    return {
        "mode": mode,
        "question": question,
        "elapsed_ms": round((time.time() - started) * 1000, 1),
        "result_excerpt": result_text[:1200],
        "has_request_id": "request_id=" in result_text,
        "has_support": "support=" in result_text,
        "has_graph_lite_summary": "graph-lite=" in result_text,
    }


def read_extension_id_from_preferences(profile_dir: str, extension_dir: Path) -> str:
    preferences_path = Path(profile_dir) / "Default" / "Preferences"
    deadline = time.time() + 15
    while time.time() < deadline:
        if preferences_path.exists():
            try:
                preferences = json.loads(preferences_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                time.sleep(0.5)
                continue
            settings = preferences.get("extensions", {}).get("settings", {})
            for extension_id, entry in settings.items():
                manifest = entry.get("manifest", {})
                extension_path = Path(str(entry.get("path", ""))).resolve()
                if manifest.get("name") == EXTENSION_NAME or extension_path == extension_dir:
                    return extension_id
        time.sleep(0.5)
    raise RuntimeError("could not resolve loaded extension id from Chrome profile preferences")


def run_smoke(args: argparse.Namespace) -> dict[str, Any]:
    extension_dir = Path(args.extension_dir).resolve()
    if not extension_dir.exists():
        raise FileNotFoundError(f"extension directory not found: {extension_dir}")

    result: dict[str, Any] = {
        "extension_dir": str(extension_dir),
        "server_url": args.server_url.rstrip("/"),
        "chrome_executable": args.chrome_executable,
        "surface": "loaded Chrome extension with sidepanel.html opened as chrome-extension page",
    }

    with tempfile.TemporaryDirectory(prefix="trunk-rag-browser-companion-") as profile_dir:
        result["profile_dir"] = profile_dir
        with sync_playwright() as playwright:
            context = playwright.chromium.launch_persistent_context(
                profile_dir,
                headless=False,
                executable_path=args.chrome_executable,
                ignore_default_args=["--disable-extensions"],
                args=[
                    f"--disable-extensions-except={extension_dir}",
                    f"--load-extension={extension_dir}",
                    "--enable-extensions",
                    "--no-first-run",
                    "--no-default-browser-check",
                    "--disable-search-engine-choice-screen",
                ],
            )
            try:
                worker = context.service_workers[0] if context.service_workers else None
                if worker is None:
                    try:
                        worker = context.wait_for_event("serviceworker", timeout=5000)
                    except PlaywrightTimeoutError:
                        worker = None
                extension_id = (
                    worker.url.split("/")[2]
                    if worker is not None
                    else read_extension_id_from_preferences(profile_dir, extension_dir)
                )
                result["extension_id"] = extension_id
                result["service_worker_url"] = worker.url if worker is not None else ""

                sidepanel = context.new_page()
                sidepanel.goto(
                    f"chrome-extension://{extension_id}/sidepanel.html",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                sidepanel.wait_for_selector("#statusText", timeout=10000)
                sidepanel.fill("#serverUrl", result["server_url"])
                sidepanel.click("#saveServerBtn")
                sidepanel.wait_for_timeout(2500)
                status_text = sidepanel.locator("#statusText").inner_text()
                if not status_text.startswith("Online"):
                    sidepanel.click("#healthBtn")
                    sidepanel.wait_for_timeout(2500)
                    status_text = sidepanel.locator("#statusText").inner_text()
                result["health_status"] = status_text
                result["health_ok"] = status_text.startswith("Online")

                result["balanced_query"] = run_query(
                    sidepanel,
                    args.balanced_question,
                    mode="balanced",
                    timeout=90000,
                )
                if args.skip_quality:
                    result["quality_query"] = {"skipped": True}
                else:
                    result["quality_query"] = run_query(
                        sidepanel,
                        args.quality_question,
                        mode="quality",
                        timeout=150000,
                    )

                content_page = context.new_page()
                content_page.goto(
                    f"{result['server_url']}/intro",
                    wait_until="domcontentloaded",
                    timeout=30000,
                )
                content_page.evaluate(
                    """() => {
                        const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
                        let node = walker.nextNode();
                        while (node && !node.textContent.trim()) node = walker.nextNode();
                        if (!node) return;
                        const range = document.createRange();
                        range.selectNodeContents(node);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }""",
                )
                content_page.bring_to_front()
                sidepanel.evaluate('document.querySelector("#capturePageBtn").click()')
                sidepanel.wait_for_function(
                    """() => {
                        const el = document.querySelector("#pageSummary");
                        return el && el.innerText && !el.innerText.includes("명시적으로");
                    }""",
                    timeout=20000,
                )
                capture_summary = sidepanel.locator("#pageSummary").inner_text()
                upload_enabled = sidepanel.locator("#uploadDraftBtn").is_enabled()
                result["capture"] = {
                    "summary": capture_summary,
                    "upload_enabled": upload_enabled,
                }

                if args.skip_upload:
                    result["upload_draft"] = {
                        "skipped": True,
                        "upload_enabled_after_capture": upload_enabled,
                    }
                else:
                    sidepanel.evaluate('document.querySelector("#uploadDraftBtn").click()')
                    sidepanel.wait_for_function(
                        """() => {
                            const el = document.querySelector("#resultPanel");
                            return el && el.innerText.includes("Upload draft");
                        }""",
                        timeout=30000,
                    )
                    upload_result = sidepanel.locator("#resultPanel").inner_text()
                    result["upload_draft"] = {
                        "result_excerpt": upload_result[:1000],
                        "created": "Upload draft created" in upload_result,
                    }
                result["sidepanel_url"] = sidepanel.url
            except PlaywrightTimeoutError as exc:
                result["error"] = f"timeout: {exc}"
                raise
            finally:
                context.close()

    return result


def main() -> int:
    args = parse_args()
    result = run_smoke(args)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output_json:
        output_path = Path(args.output_json)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
