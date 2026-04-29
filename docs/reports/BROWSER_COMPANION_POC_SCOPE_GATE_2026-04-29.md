# Browser Companion PoC Scope Gate (2026-04-29)

## Scope

- Loop: `LOOP-113 Browser companion PoC scope gate`
- Input: `docs/reports/BROWSER_EXTENSION_COMPANION_REVIEW_2026-04-29.md`
- Purpose: decide whether to build a minimal browser companion extension and define the narrow implementation boundary.

## Decision

`Go`, with a narrow local-server companion scope.

The browser extension should not replace Trunk RAG. It should be a thin Chrome MV3 side panel that makes the existing local Trunk RAG server easier to use from a browser page.

## Minimal PoC Scope

Include:

- Chrome Manifest V3 extension skeleton.
- Side panel UI.
- Local server connection status for `http://127.0.0.1:8000`.
- Question input that calls local `/query`.
- Optional current page/selection extraction on explicit user action.
- Upload request draft flow that calls local `/upload-requests`.
- Response rendering for answer, citations/support, request id, and graph-lite status.

Exclude:

- Chrome Web Store packaging.
- On-device WebGPU model runtime.
- Browser-only RAG.
- IndexedDB as Trunk RAG's document source of truth.
- Full page background crawling.
- Default broad `host_permissions` for every website.
- Any paid API or external hosted model call.

## Permission Boundary

Preferred initial permissions:

- `sidePanel`
- `storage`
- `activeTab`
- `scripting`

Preferred host permissions:

- `http://127.0.0.1/*`
- `http://localhost/*`

Avoid by default:

- `http://*/*`
- `https://*/*`

If current-page extraction needs broader access later, gate it behind explicit user action and document the permission reason before widening permissions.

## Implementation Strategy

- Use dependency-free vanilla JavaScript for the first skeleton.
- Keep files under a dedicated extension directory so the Python/FastAPI runtime is not mixed with extension code.
- Treat local server availability as optional: show disconnected state rather than failing the panel.
- Do not start or manage the local Python server from the extension in the first PoC.
- Do not change `/app` behavior while building the extension.

## Validation Plan

For the skeleton PoC:

- Validate `manifest.json` shape with a small repo-local script or Python JSON check.
- Run `node --check` on extension JavaScript files.
- Keep roadmap harness ready.
- Manual browser loading can remain a follow-up unless the user explicitly asks for interactive Chrome verification.

## Next Loop

Proceed to `LOOP-114 Browser companion extension skeleton PoC` with the narrow scope above.

