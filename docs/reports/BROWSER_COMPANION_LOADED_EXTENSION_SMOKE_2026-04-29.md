# Browser Companion Loaded-Extension Smoke (2026-04-29)

## Scope

- Loop: `LOOP-116 Browser companion loaded-extension manual smoke`
- Target: `browser_companion/` Chrome MV3 side panel companion
- Server: `http://127.0.0.1:8000`
- Evidence JSON: `docs/reports/browser_companion_loaded_extension_smoke_2026-04-29.json`

## Command

```bash
./.venv/bin/python scripts/smoke_browser_companion_extension.py \
  --chrome-executable "/Users/Agent/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --output-json docs/reports/browser_companion_loaded_extension_smoke_2026-04-29.json
```

## Result

- Overall: pass for loaded-extension transport and local-server workflow.
- Browser: Chrome for Testing from the local Playwright cache.
- Extension id: `fhebiamiikemennkopkncmjhgcdckjnj`
- Service worker: `chrome-extension://fhebiamiikemennkopkncmjhgcdckjnj/background.js`
- Surface: loaded unpacked extension with `sidepanel.html` opened as a `chrome-extension://` page.

## Step Evidence

| step | result | evidence |
| --- | --- | --- |
| Manifest/load | pass | extension id resolved and MV3 background service worker loaded |
| Local health | pass | `Online | vectors=37 | model=gemma4:e4b` |
| Balanced query | pass | `request_id=6ef2244c-3acc-4b19-86b7-6e8680c3d8ee`, `support=supported`, elapsed `10094.5ms` |
| Quality query | pass for extension/server round trip | `request_id=cd2d192a-11c3-4f85-9b2b-7c7794920f3b`, `support=supported`, elapsed `5380.1ms` |
| Graph-lite summary display | pass, no active graph snapshot on current server | UI rendered `graph-lite=-` |
| Explicit page capture | pass | `selection: Trunk RAG intro (15 chars)`, upload enabled only after capture |
| Upload draft | pass | `ef12174a-c0f9-4325-80d1-35388f73fb84 (pending)` |

## Findings

- The extension can be loaded from `browser_companion/` and can call `/health`, `/query`, and `/upload-requests` against the local Trunk RAG server.
- The permission boundary remains narrow: localhost host permissions plus explicit `activeTab`/`scripting` capture.
- The smoke created one normal pending upload request as expected. It did not bypass admin approval.
- The Quality query returned transport metadata but weak answer content (`제공된 문서에서 확인되지 않습니다.`). Treat this as RAG/model quality evidence, not an extension transport failure.
- Graph-lite did not run in this smoke because the already-running `:8000` server did not expose an active graph-lite snapshot. The UI handled that by rendering `graph-lite=-`.

## Post-Smoke Hardening Candidates

1. Add a clearer extension-side label when graph-lite metadata is absent versus disabled/fallback.
2. Add a visible model/server profile line to the side panel so slow or weak query results can be attributed quickly.
3. Add an operator note that upload smoke creates a real pending upload request in the local Trunk RAG store.
4. Consider a dedicated local smoke server profile with graph-lite enabled before repeating Quality-mode extension evidence.
