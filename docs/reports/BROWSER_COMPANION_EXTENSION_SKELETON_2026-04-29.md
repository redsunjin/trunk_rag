# Browser Companion Extension Skeleton (2026-04-29)

## Scope

- Loop: `LOOP-114 Browser companion extension skeleton PoC`
- Input: `docs/reports/BROWSER_COMPANION_POC_SCOPE_GATE_2026-04-29.md`
- Purpose: add a dependency-free Chrome MV3 side panel skeleton that connects to a local Trunk RAG server.

## Added Files

- `browser_companion/manifest.json`
- `browser_companion/background.js`
- `browser_companion/sidepanel.html`
- `browser_companion/sidepanel.css`
- `browser_companion/sidepanel.js`
- `browser_companion/README.md`
- `scripts/validate_browser_companion_manifest.py`

## Implemented Behavior

- Opens a Chrome side panel companion.
- Stores configurable local server URL, defaulting to `http://127.0.0.1:8000`.
- Checks local `/health`.
- Sends questions to local `/query` with `debug=true`.
- Supports `Balanced` and `Quality` request modes.
- Displays answer, request id, support level, citations, and graph-lite state.
- Captures current page/selection only after the user clicks `Capture`.
- Creates an upload draft through local `/upload-requests`.

## Permission Boundary

The manifest is intentionally narrow:

- permissions: `sidePanel`, `storage`, `activeTab`, `scripting`
- host_permissions: `http://127.0.0.1/*`, `http://localhost/*`

The skeleton does not request broad `http://*/*`, `https://*/*`, or `<all_urls>` host permissions.

## Validation

- `node --check browser_companion/background.js` -> pass
- `node --check browser_companion/sidepanel.js` -> pass
- `./.venv/bin/python scripts/validate_browser_companion_manifest.py` -> `browser companion manifest ok`
- `./.venv/bin/python scripts/roadmap_harness.py validate` -> ready

## Remaining Work

- Browser-loaded manual smoke is not yet executed.
- Local-server smoke plan should verify `/health`, `/query`, explicit page capture, and upload draft from the side panel.
- No Chrome Web Store packaging is attempted.

