# Quality Model Default Policy Revisit (2026-04-29)

## Scope

- Loop: `LOOP-122 Quality model default policy revisit`
- Inputs:
  - `docs/reports/GRAPH_LITE_QUALITY_PROMOTION_POLICY_2026-04-29.md`
  - `docs/reports/RAG_QUALITY_MODEL_COMPARISON_2026-04-29_GRAPH_LITE_ACTIVE_DOC_QWEN.md`
  - `docs/reports/BROWSER_COMPANION_GRAPH_LITE_ENABLED_SMOKE_2026-04-29.md`
  - `docs/reports/USER_DOC_RAG_QUALITY_FIXTURE_SEED_2026-04-29.md`
- Boundary: policy only. No default model change, no paid API, no new model install, and no large eval run.

## Decision

| Area | Decision | Reason |
| --- | --- | --- |
| Global default model | Keep current default for now | Changing the global runtime default from policy evidence alone would mix transport, retrieval, and answer-quality concerns. |
| Balanced mode | Keep low-risk default behavior | Balanced should remain predictable and should not require graph-lite or a heavier Quality model. |
| Quality graph-lite | Keep opt-in enabled | Graph-lite metadata transport is verified in `/app` and browser companion when the server has `DOC_RAG_GRAPH_LITE_SNAPSHOT_DIR`. |
| `qwen3.5:9b-nvfp4` Quality candidate | Conditional preferred candidate | Existing graph-candidate eval passed with `pass_rate=1.0`, `score=0.9167`, `p95=4468.718ms`, but it should remain an operator-selected Quality candidate until user-doc fixtures are active. |
| `gemma4:e4b` Quality default promotion | No-Go | Browser companion graph-lite smoke showed `graph-lite=hit`, `relations=8`, and `context=added`, but answer text still said `제공된 문서에서 확인되지 않습니다.` |
| User-doc fixture gate | Required before default change | `UDQ-BC-01` is candidate-only because the operator guide is not in the current RAG corpus. |

## Key Separation

Graph-lite transport passing is not the same as answer quality passing.

- Transport evidence:
  - `graph-lite=hit`
  - `relations=8`
  - `context=added`
  - request id and citations are present
- Answer-quality evidence still needed:
  - the answer uses attached graph/context correctly
  - the answer avoids false "not found" responses when sources exist
  - user/operator documents pass answer-level checks after they are indexed

## Current Policy

1. Keep graph-lite as `Quality` opt-in.
2. Keep `Balanced` as the stable default path.
3. Do not promote a heavier Quality model to global default yet.
4. Treat `qwen3.5:9b-nvfp4` as the preferred local Quality candidate for graph-heavy questions when it is installed and the operator explicitly chooses that path.
5. Require user-doc answer-level fixture evidence before changing Quality default policy.

## Required Evidence For A Future Default Change

Before changing the Quality default model or adding browser companion model override as an operator recommendation, gather:

- A managed/user-doc fixture promoted from `UDQ-BC-01` or equivalent.
- A graph-lite-enabled Quality eval against that fixture.
- A model comparison including the current default and the preferred candidate.
- Evidence that the selected model does not return false "not found" answers when support/citations/graph-lite context are present.
- p95 latency within the existing local Quality budget.

## Next Recommended Track

`LOOP-123 Project-doc ingestion path for user-doc quality gate`

Purpose:

- Decide whether project/operator docs such as `docs/BROWSER_COMPANION_OPERATOR_GUIDE.md` should be indexed through managed-doc workflow, a project-doc collection, or remain external docs only.
- Once the path is chosen, promote `UDQ-BC-01` from candidate-only to a runnable answer-level fixture.

This should happen before changing default model behavior.
