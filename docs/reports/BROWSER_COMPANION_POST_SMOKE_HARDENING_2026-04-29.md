# Browser Companion Post-Smoke Hardening (2026-04-29)

## Scope

- Loop: `LOOP-117 Browser companion post-smoke hardening`
- Input evidence: `docs/reports/BROWSER_COMPANION_LOADED_EXTENSION_SMOKE_2026-04-29.md`
- Target: `browser_companion/` side panel and smoke helper

## Implemented

- Split the health row into simple connection state plus server profile metadata.
- Exposed `model`, `runtime`, `timeout`, and `vectors` after `/health`.
- Changed missing graph-lite metadata from `graph-lite=-` to `graph-lite=not-reported`, so absent metadata is distinct from `disabled` or `fallback`.
- Added the response model to the query metadata line.
- Renamed the upload button/result to clarify that uploads become admin review drafts.
- Updated the smoke helper to accept the new upload success text.

## Deferred

- Full Chrome toolbar side-panel UI automation remains out of scope. The current helper validates the loaded extension and `sidepanel.html` document as a `chrome-extension://` page.
- A graph-lite-enabled extension smoke should be repeated later with a server started with `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR`.
- Chrome Web Store packaging, broader host permissions, and WebGPU/browser-only model runtime remain out of scope.

## Verification Target

- `node --check browser_companion/sidepanel.js`
- `./.venv/bin/python scripts/validate_browser_companion_manifest.py`
- `env PYTHONPYCACHEPREFIX=/tmp/trunk-rag-pycache ./.venv/bin/python -m py_compile scripts/smoke_browser_companion_extension.py`
- `./.venv/bin/python scripts/roadmap_harness.py validate`

## Verification Evidence

- `node --check browser_companion/sidepanel.js` passed.
- `./.venv/bin/python scripts/validate_browser_companion_manifest.py` passed.
- `env PYTHONPYCACHEPREFIX=/tmp/trunk-rag-pycache ./.venv/bin/python -m py_compile scripts/smoke_browser_companion_extension.py` passed.
- Post-hardening loaded-extension smoke passed with `--skip-quality --skip-upload` to avoid creating another pending upload request.
- Post-hardening smoke evidence: `request_id=867b7242-3ffc-4ca1-897d-cc51e5bfa66e`, `model=gemma4:e4b`, `graph-lite=not-reported`, capture summary `selection: Trunk RAG intro (15 chars)`.
