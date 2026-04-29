# Browser Companion Local-Server Smoke Plan (2026-04-29)

## Scope

- Loop: `LOOP-115 Browser companion local-server smoke plan`
- Target: `browser_companion/` Chrome MV3 side panel skeleton
- Purpose: define the manual loaded-extension smoke before expanding implementation.

## Preconditions

1. Trunk RAG local server is running.
2. Browser companion is loaded from `browser_companion/` through `chrome://extensions`.
3. Extension side panel is open.
4. Local server URL is `http://127.0.0.1:8000` unless the operator changes it.

## Smoke Steps

### 1. Manifest Load

- Open `chrome://extensions`.
- Enable Developer mode.
- Click `Load unpacked`.
- Select `browser_companion/`.

Expected:

- Extension loads without manifest errors.
- Extension action is visible.
- Side panel can open.

Evidence:

- Record Chrome extension id.
- Record any load warnings or errors.

### 2. Local Health

- Open the side panel.
- Confirm the server URL.
- Click the refresh button.

Expected:

- Connected server shows `Online`.
- Status includes vector count and default model.
- If server is down, panel shows `Disconnected` without crashing.

Evidence:

- Record status text.
- Record server URL.

### 3. Query

- Ask a short question in `Balanced`.
- Ask a relation-heavy question in `Quality`.

Expected:

- `/query` returns an answer.
- Result metadata shows request id and support level.
- Quality relation-heavy response shows graph-lite status when server debug meta includes it.

Evidence:

- Record answer snippet.
- Record `request_id`.
- Record `graph-lite=hit|fallback|disabled`.

### 4. Explicit Page Capture

- Navigate to a simple page.
- Select a short paragraph.
- Click `Capture`.

Expected:

- Panel records selected text length.
- No automatic page scraping happens before the click.
- Upload Draft becomes enabled only after capture.

Evidence:

- Record captured title and char count.

### 5. Upload Draft

- Click `Upload Draft` after capture.

Expected:

- `/upload-requests` returns request id and status.
- Draft content includes page title, source URL, and captured text.
- Admin approval remains required by normal Trunk RAG workflow.

Evidence:

- Record upload request id and status.

## Pass Criteria

- Manifest loads.
- Local health succeeds or fails gracefully.
- Query succeeds against a running local server.
- Explicit page capture is user-triggered.
- Upload draft creates a pending/rejected request without extension crash.
- No broad host permissions are required.

## Fail Criteria

- Manifest cannot load.
- Extension requires broad `http://*/*`, `https://*/*`, or `<all_urls>` permission.
- Side panel crashes when local server is unavailable.
- Current page text is captured without explicit user action.
- Upload draft bypasses normal Trunk RAG admin workflow.

## Next Loop

`LOOP-116 Browser companion loaded-extension manual smoke` should execute the steps above and record evidence before adding more extension features.

