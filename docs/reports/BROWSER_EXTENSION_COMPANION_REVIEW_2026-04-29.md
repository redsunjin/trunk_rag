# Browser Extension Companion Review (2026-04-29)

## Scope

- Trigger: review `nico-martin/gemma4-browser-extension` as a possible browser delivery shape for Trunk RAG.
- Decision type: product/architecture option review only.
- Current execution priority remains `TODO.md` active loop. This document does not replace the graph-lite Quality eval track.

## Reviewed Reference

- Repository: <https://github.com/nico-martin/gemma4-browser-extension>
- README claim: on-device Chrome extension using Transformers.js, WebGPU, and Gemma 4.
- Architecture in the reference:
  - Chrome Manifest V3 extension
  - Side panel chat UI
  - Background service worker as the AI/model/tool engine
  - Content script for page extraction/highlighting
  - Transformers.js WebGPU pipelines
  - IndexedDB vector history for semantic browsing-history search
- Model constants in the reference:
  - Text generation: `onnx-community/gemma-4-E2B-it-ONNX`
  - Embedding: `onnx-community/all-MiniLM-L6-v2-ONNX`

## External Platform Notes

- Chrome `sidePanel` is a valid companion UI surface for MV3 extensions and is available on Chrome 114+.
  - Source: <https://developer.chrome.com/docs/extensions/reference/api/sidePanel>
- Transformers.js supports browser-side model execution and WebGPU acceleration through `device: "webgpu"`.
  - Source: <https://huggingface.co/docs/transformers.js/en/guides/webgpu>
- MV3 extension service workers can be terminated after idle periods or long-running requests, so model loading/inference must be resilient to worker shutdown and cache recovery.
  - Source: <https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle>

## Fit For Trunk RAG

The reference is directionally useful, but the right fit is not to replace Trunk RAG's local FastAPI runtime.

Recommended first shape:

1. `Trunk RAG Browser Companion` extension.
2. Side panel UI for browser-native access.
3. Content script extracts current page text, selected text, headings, and URL metadata.
4. The extension calls the local Trunk RAG server at `http://127.0.0.1:8000`.
5. Trunk RAG remains responsible for `/semantic-search`, `/query`, `/upload-requests`, managed docs, admin approval, reindex, graph-lite, and quality gates.

This keeps the current operating model intact while adding a more convenient browser entry point.

## What To Avoid For Now

- Do not make browser-only RAG the default product path.
- Do not replace Chroma/managed-doc/admin workflows with IndexedDB as the source of truth.
- Do not require users to download large ONNX model weights as the main MVP path.
- Do not promote WebGPU-only execution as a guaranteed runtime baseline.
- Do not move graph-lite snapshot generation into the browser extension.

## Viable PoC

Small PoC scope:

- Side panel shows Trunk RAG connection status.
- User can ask a question from the side panel.
- User can send current page/selection as an upload request draft.
- Response displays answer, citations, support level, and graph-lite status.
- Local server remains required.

Deferred experiments:

- Browser-only current-page semantic search with Transformers.js embeddings.
- ONNX/WebGPU Gemma E2B answer mode for page-only questions.
- Offline extension-only mode for narrow, non-admin workflows.

## Decision

- Go for documentation and future-track parking.
- Do not interrupt `LOOP-111`.
- After the current graph-lite Quality evaluation and promotion policy are closed, consider a separate loop for a `Browser Companion PoC` if the user wants browser-native access.

