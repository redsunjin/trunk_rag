# Browser Companion Graph-Lite Enabled Smoke (2026-04-29)

## Scope

- Loop: `LOOP-119 Graph-lite enabled browser companion smoke`
- Target: `browser_companion/` Chrome MV3 side panel companion
- Server: `http://127.0.0.1:8014`
- Snapshot: `/tmp/trunk_rag_graph_lite_snapshot_loop119`
- Evidence JSON: `docs/reports/browser_companion_graph_lite_smoke_2026-04-29.json`

## Snapshot

```bash
./.venv/bin/python scripts/build_graph_lite_snapshot.py \
  --output-dir /tmp/trunk_rag_graph_lite_snapshot_loop119
```

Result:

- source docs: `5`
- section hits: `21`
- entities: `20`
- relations: `48`

## Server

```bash
env DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR=/tmp/trunk_rag_graph_lite_snapshot_loop119 \
  ./.venv/bin/python -m uvicorn app_api:app --host 127.0.0.1 --port 8014
```

The temporary server was stopped after the smoke. A final `/health` check on `:8014` returned connection failure, confirming the loop-specific server was no longer running.

## Smoke

```bash
./.venv/bin/python scripts/smoke_browser_companion_extension.py \
  --server-url http://127.0.0.1:8014 \
  --chrome-executable "/Users/Agent/Library/Caches/ms-playwright/chromium-1208/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing" \
  --quality-question "에콜 폴리테크니크, 훔볼트 대학, 왕립학회, 파도바 대학을 한 관계망으로 놓고 각자의 역할을 설명해줘." \
  --skip-upload \
  --expect-quality-graph-lite-status hit \
  --expect-quality-min-graph-lite-relations 1 \
  --output-json docs/reports/browser_companion_graph_lite_smoke_2026-04-29.json
```

## Result

- Overall: pass for browser companion graph-lite status transport.
- Extension id: `fhebiamiikemennkopkncmjhgcdckjnj`
- Health: `Online`
- Balanced query: `graph-lite=disabled`, `relations=0`, request id `9ae7be2b-fc5e-498e-9e8e-d1aef76f2d24`
- Quality query: `graph-lite=hit`, `relations=8`, `context=added`, request id `bdb67099-f084-46ee-8d60-3c36fcd96589`
- Quality support/citations: `support=supported`, sources `fr.md | ge.md | it.md`
- Upload draft: skipped intentionally to avoid creating another pending upload request.

## Interpretation

- The browser companion can display graph-lite enabled Quality metadata when the local server is started with `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR`.
- The prior `graph-lite=not-reported` smoke was caused by a server without an active graph-lite snapshot, not by extension transport.
- The answer text remained weak (`제공된 문서에서 확인되지 않습니다.`) even though graph-lite context was attached. Treat this as a model/prompt/quality issue for the next RAG quality loops, not as a browser companion failure.

## Follow-Up

1. `LOOP-120`: add operator-facing browser companion guide and troubleshooting notes.
2. `LOOP-121`: seed user/managed-doc quality fixtures so graph-lite hit is evaluated against answer quality, not only metadata transport.
3. `LOOP-122`: revisit Quality model default policy after user-doc fixture evidence.
