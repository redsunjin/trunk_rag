# Trunk RAG Modern UI Design

## Goal

Modernize the Trunk RAG web UI without changing product scope or backend behavior. The first implementation pass focuses on `/app`; `/intro` and `/admin` should inherit the same visual language in later loops.

## Product Thesis

Trunk RAG should feel like a quiet local research workspace, not a flashy AI console. The default experience should help a non-expert ask questions, read grounded answers, and inspect sources without understanding runtime diagnostics. Advanced users should be able to open a richer workspace panel for evidence, routing, graph-lite, runtime, and request details.

## Confirmed Direction

- Default UX: `Research Studio`
- Advanced UX: `AI Workspace` behavior exposed through an advanced mode
- Advanced mode placement: right-side `Advanced Rail` on desktop
- Visual tone: `Quiet Lab`
- First implementation target: `/app`

## Out of Scope

- Dark `Signal Console` theme
- Full GraphRAG or Neo4j scope changes
- Backend API contract changes
- Replacing the current plain HTML/CSS/JS frontend stack
- Desktop packaging or browser companion redesign
- `/intro` and `/admin` full redesign in the first pass

## User Experience

### Default Research Studio

The default `/app` screen should prioritize:

- Asking a document-grounded question
- Selecting a simple answer mode
- Reading the answer
- Reading sources and support labels
- Sending answer feedback
- Creating a document update request when needed

Runtime, ops-baseline, graph-lite, request id, and collection routing details should not dominate the default view. They can appear as compact status text, but detailed diagnostics belong in advanced mode.

### Advanced Rail

Desktop advanced mode opens a right-side rail. It should contain dense but organized controls and evidence:

- Selected collection and routing details
- Balanced/Quality mode details
- Graph-lite status and relation count
- Citation/support summary
- Request id and model/runtime profile
- Recent ops/user-doc gate summary when available
- Upload/admin workflow entry points that are useful for power users

The rail should be toggleable from the main `/app` header or query controls. Its open/closed state should persist in `localStorage`.

### Mobile Behavior

On narrow screens, the advanced rail should become a bottom drawer or full-width collapsible panel. It must not create horizontal overflow or cover the query/answer controls in a way that prevents normal use.

## Visual Direction

### Quiet Lab

Use a bright, restrained research-tool palette:

- Base: off-white and warm-neutral light gray
- Text: near-black neutral
- Accent: one deep green for primary actions and active states
- Secondary states: muted slate/olive neutrals
- Error/warning states: keep existing semantic colors readable and restrained

Avoid:

- Heavy gradients
- Purple/blue AI-dashboard styling
- Dense card wallpaper
- Large decorative hero areas inside the app
- Dark console-first UI

### Layout Principles

- Prefer unframed workspace sections over nested cards.
- Use thin separators, spacing, and alignment before shadows.
- Keep repeated item cards only where the user scans independent records.
- Keep controls dense enough for repeated work but not cramped.
- Use stable dimensions for mode controls, toolbar buttons, source rows, and rail sections.

## Interaction Rules

- `Advanced` toggle opens/closes the rail and stores state in `localStorage`.
- Balanced/Quality selection remains visible in the default query area.
- Answer loading should use a small, clear progress state rather than large decorative animation.
- Source and support details should be readable directly after the answer.
- Advanced details should not shift the main answer layout unexpectedly.

## Accessibility And Responsiveness

- Preserve keyboard access for query controls, mode selection, upload request controls, and advanced toggle.
- Maintain readable contrast in default and advanced surfaces.
- Avoid viewport-width font scaling.
- Prevent horizontal overflow at mobile widths.
- Ensure long Korean and English labels wrap or truncate cleanly.

## Implementation Notes

Expected first-pass files:

- `web/index.html`: restructure `/app` layout only where needed.
- `web/styles.css`: introduce Quiet Lab tokens and responsive advanced rail styles.
- `web/js/app_page.js`: add advanced mode toggle state and wire existing diagnostic data into the rail.
- `tests/e2e/test_web_flow_playwright.py`: verify default `/app`, advanced mode, and mobile overflow behavior.
- `tests/api/test_system_api.py` or existing API tests only if UI copy depends on response contract changes; no API changes are intended.

Do not move to a frontend framework. The current static HTML/CSS/JS structure is sufficient for the first pass.

## Verification Plan

Minimum verification for implementation:

- `node --check web/js/app_page.js`
- `./.venv/bin/python -m pytest -q tests/e2e/test_web_flow_playwright.py`
- `./.venv/bin/python -m pytest -q tests/api/test_system_api.py`
- Browser or Playwright render check for desktop and mobile widths
- `./.venv/bin/python scripts/roadmap_harness.py validate`
- `./.venv/bin/python scripts/session_closeout.py --allow-dirty` during WIP and without `--allow-dirty` after commit

## Open Decisions

None for the first implementation pass. Later loops can decide whether `/intro` and `/admin` receive full layout changes or only color/type/token alignment.

## Self-Review

- Placeholder scan: no unresolved placeholders.
- Internal consistency: first pass is scoped to `/app`; `/intro` and `/admin` are explicitly later work.
- Scope check: this is one UI modernization loop, not a backend or product-scope expansion.
- Ambiguity check: advanced mode is desktop right rail and mobile drawer/collapsible panel.
