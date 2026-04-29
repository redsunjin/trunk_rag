# Trunk RAG Browser Companion

Minimal Chrome Manifest V3 side panel companion for a local Trunk RAG server.

## Boundary

- Connects to an already running local Trunk RAG server.
- Does not start Python, Ollama, or Chroma.
- Does not run an on-device browser model.
- Does not replace `/app`, `/admin`, or managed-doc workflows.

## Local Load

1. Start Trunk RAG locally.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Load unpacked from `browser_companion/`.
5. Open the extension side panel and check local server status.

## Smoke Helper

Use the helper when Chrome for Testing is available through Playwright:

```bash
./.venv/bin/python scripts/smoke_browser_companion_extension.py \
  --chrome-executable "/Users/Agent/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --output-json docs/reports/browser_companion_loaded_extension_smoke_2026-04-29.json
```

The smoke creates a normal pending upload request when the upload step succeeds.
Use `--skip-upload` when checking UI changes without creating another local request.

## Permissions

The skeleton intentionally keeps host permissions limited to localhost:

- `http://127.0.0.1/*`
- `http://localhost/*`

Current page capture is explicit and uses `activeTab` + `scripting`.
