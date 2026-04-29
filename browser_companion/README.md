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

## Permissions

The skeleton intentionally keeps host permissions limited to localhost:

- `http://127.0.0.1/*`
- `http://localhost/*`

Current page capture is explicit and uses `activeTab` + `scripting`.
