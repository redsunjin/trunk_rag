# Browser Companion Operator Guide

## Purpose

The browser companion is a Chrome MV3 side panel for an already running local Trunk RAG server. It is a companion surface only:

- It does not start Python, Ollama, Chroma, or graph-lite.
- It does not replace `/app`, `/admin`, or managed-doc approval.
- It uses localhost-only host permissions.
- It reads the current page only after the operator clicks `Capture`.

## Normal Local Use

1. Start Trunk RAG with the normal local server path.
2. Open `chrome://extensions`.
3. Enable Developer mode.
4. Load unpacked from `browser_companion/`.
5. Open the side panel.
6. Confirm the Local server URL.
7. Click the refresh button.
8. Ask in `Balanced` for normal local RAG.
9. Ask relation-heavy questions in `Quality`.

Expected health state:

- Status: `Online`
- Server profile line: `model=... | runtime=... | timeout=...s | vectors=...`

## Graph-Lite Quality Smoke

Build a current graph-lite snapshot:

```bash
./.venv/bin/python scripts/build_graph_lite_snapshot.py \
  --output-dir /tmp/trunk_rag_graph_lite_snapshot_operator
```

Start a graph-lite-enabled local server on a separate port:

```bash
env DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR=/tmp/trunk_rag_graph_lite_snapshot_operator \
  ./.venv/bin/python -m uvicorn app_api:app --host 127.0.0.1 --port 8014
```

Set the side panel Local server URL to:

```text
http://127.0.0.1:8014
```

Ask a relation-heavy `Quality` question. A healthy graph-lite transport should show:

```text
graph-lite=hit | relations=<number> | context=added
```

Automated loaded-extension smoke:

```bash
./.venv/bin/python scripts/smoke_browser_companion_extension.py \
  --server-url http://127.0.0.1:8014 \
  --chrome-executable "/Users/Agent/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --quality-question "에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학을 한 관계망으로 놓고 각자의 역할을 설명해줘." \
  --skip-upload \
  --expect-quality-graph-lite-status hit \
  --expect-quality-min-graph-lite-relations 1 \
  --output-json docs/reports/browser_companion_graph_lite_smoke_YYYY-MM-DD.json
```

## Graph-Lite Status Meanings

| status | meaning | operator action |
| --- | --- | --- |
| `hit` | Quality mode found relation context and appended it to RAG context. | Treat transport as healthy; evaluate answer quality separately. |
| `disabled` | Current query path does not opt into graph-lite, normally `Balanced`. | Use `Quality` for relation-heavy questions. |
| `not-reported` | Server response did not include graph-lite metadata. | Confirm server was started with current code and debug metadata. |
| `fallback` | Graph-lite ran but did not add context, such as no query entities or no relation hits. | Try a more explicit relation-heavy question or rebuild snapshot. |
| `not_run` | Graph-lite was enabled in the stage but did not complete before response metadata. | Check server logs and repeat with the smoke helper. |

## Upload Draft Behavior

`Upload Draft for Review` creates a normal upload request in the local Trunk RAG store.

- It stays under the existing admin approval workflow.
- It does not approve or index the content by itself.
- Use `--skip-upload` in smoke runs unless you intentionally want a pending request.
- Existing pending requests should not be deleted without operator confirmation.

## Troubleshooting

| symptom | likely cause | next step |
| --- | --- | --- |
| `Disconnected` | Server is down or URL/port is wrong. | Start the server and click refresh. |
| `Online` but `vectors=0` | Index is missing or wrong persist directory. | Rebuild/reindex before query smoke. |
| `graph-lite=not-reported` | Server is not exposing graph-lite metadata. | Use current code path and run against `/query` with debug metadata. |
| `graph-lite=disabled` in Quality | Side panel did not send Quality mode or old extension is loaded. | Reload the unpacked extension and confirm mode selector. |
| `graph-lite=fallback` | Snapshot has no useful match for the question. | Rebuild snapshot and use explicit entity/institution names. |
| `graph-lite=hit` but weak answer | Context transport worked but model/prompt quality failed. | Move the question into answer-level quality fixtures and compare models. |
| Capture fails | Chrome page disallows scripting or there is no active tab. | Try a normal local page such as `/intro`. |
| Upload creates an unexpected item | Upload smoke was run without `--skip-upload`. | Review it in `/admin`; deletion requires explicit operator confirmation. |

## Evidence

- Local loaded-extension smoke: `docs/reports/BROWSER_COMPANION_LOADED_EXTENSION_SMOKE_2026-04-29.md`
- Post-smoke hardening: `docs/reports/BROWSER_COMPANION_POST_SMOKE_HARDENING_2026-04-29.md`
- Graph-lite enabled smoke: `docs/reports/BROWSER_COMPANION_GRAPH_LITE_ENABLED_SMOKE_2026-04-29.md`
