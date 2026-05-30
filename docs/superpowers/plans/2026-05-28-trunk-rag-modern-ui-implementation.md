# Trunk RAG Modern UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the approved `/app` UI modernization: Quiet Lab visual tone, Research Studio default layout, and a toggleable right-side Advanced Rail.

**Architecture:** Keep the current static HTML/CSS/JS frontend. Add semantic app-shell markup in `web/index.html`, Quiet Lab layout/style tokens in `web/styles.css`, and small advanced-mode state/render helpers in `web/js/app_page.js`. Preserve backend/API contracts and existing query/upload behavior.

**Tech Stack:** Plain HTML, CSS, vanilla ES modules, FastAPI static serving, Playwright e2e tests.

---

## Files

- Modify: `web/index.html`
  - Add `app-shell`, `research-studio`, and `advanced-rail` structure.
  - Add `advancedModeToggle` control.
  - Keep existing legacy settings sidebar, document viewer, upload form, and query controls.
- Modify: `web/styles.css`
  - Add Quiet Lab tokens and responsive app shell styles.
  - Style Advanced Rail and mobile drawer behavior.
  - Avoid framework migration and avoid dark theme.
- Modify: `web/js/app_page.js`
  - Add localStorage-backed advanced rail toggle.
  - Populate rail summary from current collection/mode/health/query metadata.
- Modify: `tests/e2e/test_web_flow_playwright.py`
  - Add assertions for default Research Studio layout, Advanced Rail toggle persistence, and mobile overflow.
- Optional Modify: `README.md`, `SPEC.md`, `TODO.md`, `NEXT_SESSION_PLAN.md`
  - Only update after implementation behavior is verified.

## Task 1: Add Failing E2E Coverage For Modern App Shell

**Files:**
- Modify: `tests/e2e/test_web_flow_playwright.py`

- [x] **Step 1: Add default layout and advanced rail assertions**

Insert this block inside `test_intro_app_flow`, immediately after:

```python
expect(page.locator(".app-overview-card")).to_contain_text("유럽 과학사 샘플 데모")
```

Add:

```python
    expect(page.locator(".research-studio-shell")).to_be_visible()
    expect(page.locator(".research-hero")).to_contain_text("문서 기반으로 질문")
    expect(page.locator("#advancedModeToggle")).to_be_visible()
    expect(page.locator("#advancedRail")).to_have_attribute("aria-hidden", "true")
    expect(page.locator("#advancedRail")).to_be_hidden()
    expect(page.locator(".research-studio-shell")).not_to_contain_text("request_id=")
```

- [x] **Step 2: Add advanced rail toggle assertions**

Insert this block after the existing quality mode hint assertion:

```python
expect(page.locator("#qualityModeHint")).to_contain_text("e2b")
```

Add:

```python
    page.click("#advancedModeToggle")
    expect(page.locator("#advancedRail")).to_have_attribute("aria-hidden", "false")
    expect(page.locator("#advancedRail")).to_be_visible()
    expect(page.locator("#advancedRail")).to_contain_text("Advanced Rail")
    expect(page.locator("#advancedRailMode")).to_contain_text("balanced")
    page.reload(wait_until="domcontentloaded")
    expect(page.locator("#advancedRail")).to_have_attribute("aria-hidden", "false")
```

- [x] **Step 3: Add query metadata rail assertions**

Insert this block immediately after:

```python
expect(page.locator(".chat-message.bot").last).to_contain_text("graph-lite=disabled")
```

Add:

```python
    expect(page.locator("#advancedRail")).to_contain_text("req-e2e-1")
    expect(page.locator("#advancedRail")).to_contain_text("supported")
    expect(page.locator("#advancedRail")).to_contain_text("graph-lite=disabled")
```

Insert this block immediately after:

```python
expect(page.locator(".chat-message.bot").last).to_contain_text("relations=2")
```

Add:

```python
    expect(page.locator("#advancedRail")).to_contain_text("graph-lite=hit")
    expect(page.locator("#advancedRail")).to_contain_text("relations=2")
```

- [x] **Step 4: Add mobile overflow assertion**

Add this new test near the end of the file, before `test_admin_search_filters_flow`:

```python
@pytest.mark.e2e
def test_app_modern_layout_mobile_has_no_horizontal_overflow(page: Page, live_server_url: str):
    page.set_viewport_size({"width": 390, "height": 844})
    page.goto(f"{live_server_url}/app", wait_until="domcontentloaded")
    expect(page.locator(".research-studio-shell")).to_be_visible(timeout=15000)
    page.click("#advancedModeToggle")
    expect(page.locator("#advancedRail")).to_be_visible()
    overflow = page.evaluate(
        "() => document.documentElement.scrollWidth > document.documentElement.clientWidth"
    )
    assert overflow is False
```

- [x] **Step 5: Run the new tests and verify RED**

Run:

```bash
./.venv/bin/python -m pytest -q tests/e2e/test_web_flow_playwright.py::test_intro_app_flow tests/e2e/test_web_flow_playwright.py::test_app_modern_layout_mobile_has_no_horizontal_overflow
```

Expected: FAIL because `.research-studio-shell`, `#advancedModeToggle`, and `#advancedRail` do not exist yet.

## Task 2: Restructure `/app` Markup Into Research Studio + Advanced Rail

**Files:**
- Modify: `web/index.html`

- [x] **Step 1: Add Advanced toggle in the main header**

In `web/index.html`, inside `<header class="main-header">`, after the closing `</div>` for `.header-left`, add:

```html
        <div class="header-actions">
          <button id="advancedModeToggle" class="secondary-btn advanced-toggle" type="button" aria-controls="advancedRail" aria-expanded="false">
            Advanced
          </button>
        </div>
```

- [x] **Step 2: Wrap overview, chat, and document viewer in a modern app shell**

In `web/index.html`, replace the block starting at:

```html
      <section class="card app-overview-card">
```

and ending before:

```html
    </main>
```

with:

```html
      <div class="research-studio-shell">
        <div class="research-studio-main">
          <section class="research-hero" aria-labelledby="researchHeroTitle">
            <div>
              <p class="brand-kicker">Research Studio</p>
              <h2 id="researchHeroTitle">문서 기반으로 질문하기</h2>
              <p class="status-msg">
                기본 화면은 질문, 답변, 근거 읽기에 집중합니다. 런타임과 route 세부 정보는 Advanced Rail에서 확인합니다.
              </p>
            </div>
            <div class="research-hero-status" id="appOverviewRuntime">
              기본 런타임과 복구 경로를 확인 중입니다.
            </div>
          </section>

          <section class="app-overview-card quiet-panel">
            <h3>로컬 RAG 작업 공간</h3>
            <p class="status-msg">
              현재 기본 문서는 첫 실행 확인용 유럽 과학사 샘플 데모입니다. 내 문서는 왼쪽의 문서 추가/갱신 요청을 보내고 관리자 승인 후 반영합니다.
            </p>
            <details class="disclosure-panel compact">
              <summary>운영/복구 상세</summary>
              <div class="recovery-panel compact flat" aria-labelledby="appRecoveryTitle">
                <div class="panel-heading">
                  <h3 id="appRecoveryTitle">복구 체크</h3>
                  <span class="status-badge">runtime</span>
                </div>
                <ol id="appRecoverySteps" class="recovery-steps">
                  <li>/health 응답을 확인 중입니다.</li>
                </ol>
              </div>
              <p id="appOpsBaselineMsg" class="status-msg">
                최근 ops-baseline 게이트 상태를 확인 중입니다.
              </p>
            </details>
          </section>

          <section class="chat-layout research-chat">
            <div class="main-chat-container" id="chatContainer">
              <div class="chat-message bot">
                안녕하세요. 문서 기반 RAG 어시스턴트입니다. 질문을 입력해 주세요.
              </div>
            </div>
            <div class="quality-mode-panel" aria-label="질의 모드 선택">
              <div class="segmented-control">
                <label class="segmented-option">
                  <input type="radio" name="qualityMode" value="semantic">
                  <span>Semantic</span>
                </label>
                <label class="segmented-option">
                  <input type="radio" name="qualityMode" value="balanced" checked>
                  <span>Balanced</span>
                </label>
                <label class="segmented-option">
                  <input type="radio" name="qualityMode" value="quality">
                  <span>Quality</span>
                </label>
              </div>
              <p id="qualityModeHint" class="helper-text">시맨틱 검색 후 e2b 빠른 답변을 만들고, 복합/근거 부족 답변은 quality로 승격합니다.</p>
            </div>
            <div class="main-chat-input">
              <textarea id="userInput" rows="2" placeholder="질문을 입력하세요..."></textarea>
              <button id="sendBtn" class="primary-btn">Send</button>
            </div>
            <p class="helper-text" style="margin-top:8px;">답변 아래에서 sources와 feedback을 확인하고, Advanced Rail에서 route/request/graph-lite 상세를 볼 수 있습니다.</p>
          </section>

          <section class="doc-viewer-layout">
            <div class="quiet-panel">
              <h3 id="docTitle">Document Viewer</h3>
              <div class="doc-viewer-body" id="docViewer">
                <p class="status-msg">왼쪽 문서 목록에서 파일을 선택하면 내용을 볼 수 있습니다.</p>
              </div>
            </div>
          </section>
        </div>

        <aside class="advanced-rail" id="advancedRail" aria-hidden="true" aria-label="Advanced Rail">
          <div class="advanced-rail-header">
            <div>
              <p class="brand-kicker">Power User</p>
              <h3>Advanced Rail</h3>
            </div>
            <button id="advancedRailClose" class="secondary-btn" type="button">Close</button>
          </div>
          <div class="advanced-rail-section">
            <h4>Mode</h4>
            <p id="advancedRailMode" class="status-msg">mode=balanced</p>
          </div>
          <div class="advanced-rail-section">
            <h4>Collection Route</h4>
            <p id="advancedRailCollections" class="status-msg">collection=all</p>
          </div>
          <div class="advanced-rail-section">
            <h4>Runtime</h4>
            <p id="advancedRailRuntime" class="status-msg">runtime 확인 전입니다.</p>
          </div>
          <div class="advanced-rail-section">
            <h4>Evidence</h4>
            <p id="advancedRailEvidence" class="status-msg">아직 질의 응답이 없습니다.</p>
          </div>
          <div class="advanced-rail-section">
            <h4>Graph-Lite</h4>
            <p id="advancedRailGraphLite" class="status-msg">graph-lite=not-reported</p>
          </div>
        </aside>
      </div>
```

- [x] **Step 3: Run the targeted test and verify partial GREEN**

Run:

```bash
./.venv/bin/python -m pytest -q tests/e2e/test_web_flow_playwright.py::test_intro_app_flow
```

Expected: still FAIL because Advanced Rail JavaScript state is not wired yet, but selectors now exist.

## Task 3: Add Quiet Lab CSS And Responsive Advanced Rail

**Files:**
- Modify: `web/styles.css`

- [x] **Step 1: Update root tokens**

At the top of `web/styles.css`, replace the existing `:root` block with:

```css
:root {
    --bg-color: #f6f8f5;
    --surface-color: #ffffff;
    --surface-soft: #f1f5f1;
    --sidebar-bg: #ffffff;
    --text-primary: #111d18;
    --text-secondary: #5b6a62;
    --text-muted: #7b8a82;
    --border-color: #d9e2dd;
    --border-strong: #c6d2cc;
    --primary-color: #1f6f5b;
    --primary-hover: #175746;
    --accent-color: #b27a2c;
    --secondary-color: #eef3f0;
    --card-bg: #ffffff;
    --bot-msg-bg: #f7faf7;
    --user-msg-bg: #e3f1ec;
    --shadow: 0 8px 24px rgba(17, 29, 24, 0.06);
}
```

- [x] **Step 2: Add app shell styles**

Insert this block before the existing `/* Main Content */` comment:

```css
.quiet-panel {
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 16px;
}

.research-studio-shell {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(260px, 320px);
    gap: 18px;
    align-items: start;
}

.research-studio-main {
    min-width: 0;
}

.research-hero {
    display: grid;
    grid-template-columns: minmax(0, 1fr) minmax(180px, 260px);
    gap: 18px;
    align-items: end;
    padding: 18px 0 20px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 16px;
}

.research-hero h2 {
    font-size: 1.6rem;
    line-height: 1.2;
    margin-bottom: 8px;
}

.research-hero-status {
    min-height: 56px;
    padding: 12px;
    border: 1px solid var(--border-color);
    border-radius: 8px;
    background: var(--surface-soft);
    color: var(--text-secondary);
    font-size: 0.84rem;
    overflow-wrap: anywhere;
}

.research-chat {
    min-height: 520px;
}

.advanced-toggle[aria-expanded="true"] {
    border-color: var(--primary-color);
    color: var(--primary-color);
    background: #e7f2ee;
}

.advanced-rail {
    display: none;
    position: sticky;
    top: 24px;
    max-height: calc(100vh - 48px);
    overflow-y: auto;
    background: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: 8px;
    padding: 14px;
}

.advanced-rail.active {
    display: block;
}

.advanced-rail-header {
    display: flex;
    justify-content: space-between;
    gap: 10px;
    align-items: flex-start;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border-color);
    margin-bottom: 12px;
}

.advanced-rail-header h3 {
    font-size: 1rem;
}

.advanced-rail-section {
    padding: 12px 0;
    border-bottom: 1px solid var(--border-color);
}

.advanced-rail-section:last-child {
    border-bottom: 0;
}

.advanced-rail-section h4 {
    font-size: 0.78rem;
    color: var(--text-secondary);
    margin-bottom: 6px;
    text-transform: uppercase;
}
```

- [x] **Step 3: Add responsive behavior**

Inside the existing mobile media query in `web/styles.css`, add:

```css
    .research-studio-shell {
        display: block;
    }

    .research-hero {
        grid-template-columns: 1fr;
        gap: 12px;
    }

    .advanced-rail {
        position: static;
        max-height: none;
        margin-top: 14px;
    }

    .quality-mode-panel {
        grid-template-columns: 1fr;
    }
```

- [x] **Step 4: Run CSS-sensitive e2e test**

Run:

```bash
./.venv/bin/python -m pytest -q tests/e2e/test_web_flow_playwright.py::test_app_modern_layout_mobile_has_no_horizontal_overflow
```

Expected: still FAIL until JavaScript toggles `.active`, then pass after Task 4.

## Task 4: Wire Advanced Rail State And Metadata Rendering

**Files:**
- Modify: `web/js/app_page.js`

- [x] **Step 1: Add element references and state**

Near the other top-level element references, after:

```javascript
const qualityModeHint = document.getElementById("qualityModeHint");
```

add:

```javascript
const advancedModeToggle = document.getElementById("advancedModeToggle");
const advancedRail = document.getElementById("advancedRail");
const advancedRailClose = document.getElementById("advancedRailClose");
const advancedRailMode = document.getElementById("advancedRailMode");
const advancedRailCollections = document.getElementById("advancedRailCollections");
const advancedRailRuntime = document.getElementById("advancedRailRuntime");
const advancedRailEvidence = document.getElementById("advancedRailEvidence");
const advancedRailGraphLite = document.getElementById("advancedRailGraphLite");
```

After:

```javascript
let uploadMetadataOpen = false;
```

add:

```javascript
const ADVANCED_RAIL_STORAGE_KEY = "trunkRagAdvancedRailOpen";
let advancedRailOpen = localStorage.getItem(ADVANCED_RAIL_STORAGE_KEY) === "1";
```

- [x] **Step 2: Add rail render helpers**

After `function updateQualityModeHint() { ... }`, add:

```javascript
function selectedCollectionKeys() {
  return [collection.value || "all", collection2.value || ""].filter(Boolean);
}

function renderAdvancedRailCollections() {
  if (!advancedRailCollections) return;
  advancedRailCollections.textContent = `collections=${selectedCollectionKeys().join(",")}`;
}

function renderAdvancedRailMode() {
  if (!advancedRailMode) return;
  advancedRailMode.textContent = `mode=${getQualityMode()}`;
}

function renderAdvancedRailRuntime(data = lastHealth) {
  if (!advancedRailRuntime) return;
  if (!data) {
    advancedRailRuntime.textContent = "runtime 확인 전입니다.";
    return;
  }
  const profile = data.runtime_query_budget_profile || data.runtime_profile_status || "-";
  const modelName = data.default_llm_model || model.value || "-";
  const vectors = typeof data.vectors === "number" ? data.vectors : "-";
  advancedRailRuntime.textContent = `profile=${profile} | model=${modelName} | vectors=${vectors}`;
}

function renderAdvancedRailFromMeta(meta) {
  if (!meta || typeof meta !== "object") return;
  if (advancedRailEvidence) {
    const requestId = meta.request_id || "-";
    const support = meta.support_level || "-";
    const citations = Array.isArray(meta.citations) ? meta.citations.length : 0;
    advancedRailEvidence.textContent = `request_id=${requestId} | support=${support} | citations=${citations}`;
  }
  if (advancedRailGraphLite) {
    advancedRailGraphLite.textContent = buildGraphLiteSummary(meta) || "graph-lite=not-reported";
  }
}

function setAdvancedRailOpen(open) {
  advancedRailOpen = Boolean(open);
  if (advancedRail) {
    advancedRail.classList.toggle("active", advancedRailOpen);
    advancedRail.setAttribute("aria-hidden", advancedRailOpen ? "false" : "true");
  }
  if (advancedModeToggle) {
    advancedModeToggle.setAttribute("aria-expanded", advancedRailOpen ? "true" : "false");
    advancedModeToggle.textContent = advancedRailOpen ? "Advanced On" : "Advanced";
  }
  localStorage.setItem(ADVANCED_RAIL_STORAGE_KEY, advancedRailOpen ? "1" : "0");
}

function refreshAdvancedRail() {
  renderAdvancedRailMode();
  renderAdvancedRailCollections();
  renderAdvancedRailRuntime();
}
```

- [x] **Step 3: Call rail helpers from existing flows**

In `updateQualityModeHint()`, after setting the hint text, add:

```javascript
  renderAdvancedRailMode();
```

In collection change event handlers near the bottom of the file, add `renderAdvancedRailCollections` as a listener:

```javascript
collection.addEventListener("change", renderAdvancedRailCollections);
collection2.addEventListener("change", renderAdvancedRailCollections);
```

Where health data is assigned to `lastHealth`, add:

```javascript
  renderAdvancedRailRuntime(data);
```

If the local variable is not named `data`, use the health response object already passed to `renderHealth`/`updateHealth` in the current file.

In the query success path after response `meta` is available and before appending details, add:

```javascript
  renderAdvancedRailFromMeta(data.meta);
```

Use the response object variable already present in the current query handler.

- [x] **Step 4: Add toggle event listeners**

Near the bottom of `web/js/app_page.js`, with the other event listeners, add:

```javascript
advancedModeToggle?.addEventListener("click", () => {
  setAdvancedRailOpen(!advancedRailOpen);
});

advancedRailClose?.addEventListener("click", () => {
  setAdvancedRailOpen(false);
});

setAdvancedRailOpen(advancedRailOpen);
refreshAdvancedRail();
```

- [x] **Step 5: Run JavaScript syntax check**

Run:

```bash
node --check web/js/app_page.js
```

Expected: pass.

## Task 5: Verify The Modern UI Flow

**Files:**
- Modify: `tests/e2e/test_web_flow_playwright.py`
- No code changes expected outside fixes from prior tasks.

- [x] **Step 1: Run targeted e2e**

Run:

```bash
./.venv/bin/python -m pytest -q tests/e2e/test_web_flow_playwright.py::test_intro_app_flow tests/e2e/test_web_flow_playwright.py::test_app_modern_layout_mobile_has_no_horizontal_overflow
```

Expected: pass.

- [x] **Step 2: Run broader web/API regression**

Run:

```bash
./.venv/bin/python -m pytest -q tests/api/test_system_api.py tests/e2e/test_web_flow_playwright.py
```

Expected: pass.

- [x] **Step 3: Run static checks**

Run:

```bash
node --check web/js/app_page.js
git diff --check
./.venv/bin/python scripts/roadmap_harness.py validate
./.venv/bin/python scripts/session_closeout.py --allow-dirty
```

Expected: all ready/pass. `session_closeout.py --allow-dirty` may warn about WIP changes before commit.

## Task 6: Document And Close Out The Implementation Execution Loop

**Files:**
- Modify: `TODO.md`
- Modify: `NEXT_SESSION_PLAN.md`
- Optional Modify: `README.md`
- Optional Modify: `SPEC.md`

- [x] **Step 1: Promote the implementation loop**

In `TODO.md` `Execution Queue`, set:

```markdown
| LOOP-146 | done | Await implementation execution after modern UI plan | `./.venv/bin/python scripts/session_closeout.py` |
| LOOP-147 | active | Modern /app Research Studio UI implementation | `node --check web/js/app_page.js` + `./.venv/bin/python -m pytest -q tests/api/test_system_api.py tests/e2e/test_web_flow_playwright.py` + `./.venv/bin/python scripts/session_closeout.py` |
```

- [x] **Step 2: Add implementation notes**

Add a new `## 현재 Active Loop (LOOP-147)` section near the current active loop area in `TODO.md` with:

```markdown
## 현재 Active Loop (LOOP-147)

목표:
- `/app`를 Quiet Lab 톤의 Research Studio 기본 화면과 오른쪽 Advanced Rail 고급 모드로 개편한다.

범위:
- 포함: `web/index.html`, `web/styles.css`, `web/js/app_page.js`, `/app` e2e coverage
- 제외: `/intro`/`/admin` 전체 redesign, dark theme, backend/API contract 변경, frontend framework 교체

완료 기준:
- 기본 `/app` 화면에서 Research Studio 구조가 보인다.
- Advanced Rail이 토글되고 localStorage에 유지된다.
- query response meta가 Advanced Rail에 request/support/graph-lite 요약으로 표시된다.
- mobile width에서 horizontal overflow가 없다.

검증:
- `node --check web/js/app_page.js`
- `./.venv/bin/python -m pytest -q tests/api/test_system_api.py tests/e2e/test_web_flow_playwright.py`
- `./.venv/bin/python scripts/session_closeout.py`
```

- [x] **Step 3: Update `NEXT_SESSION_PLAN.md`**

Update `Session Loop Harness` to:

```markdown
- current_active_id: `LOOP-147`
- current_active_title: `Modern /app Research Studio UI implementation`
```

Add a dated snapshot:

```markdown
## 2026-05-28 Modern App UI Implementation Snapshot

- 현재 active: `LOOP-147 Modern /app Research Studio UI implementation`
- plan: `docs/superpowers/plans/2026-05-28-trunk-rag-modern-ui-implementation.md`
- design spec: `docs/superpowers/specs/2026-05-28-trunk-rag-modern-ui-design.md`
- scope: `/app` Quiet Lab Research Studio + right Advanced Rail only
- verification: `node --check web/js/app_page.js`, web e2e/API regression, `session_closeout.py`
```

- [x] **Step 4: Commit**

Run:

```bash
git add web/index.html web/styles.css web/js/app_page.js tests/e2e/test_web_flow_playwright.py TODO.md NEXT_SESSION_PLAN.md
git commit -m "LOOP-147 modernize app research studio UI"
```

Expected: commit succeeds.

## Self-Review

- Spec coverage: covers `/app`, Research Studio default, Advanced Rail, Quiet Lab tone, mobile behavior, no backend/API change.
- Placeholder scan: no unresolved `TBD`/`FIXME` placeholders; `TODO.md` mentions are target document names, not implementation placeholders.
- Type/name consistency: planned ids are `advancedModeToggle`, `advancedRail`, `advancedRailClose`, `advancedRailMode`, `advancedRailCollections`, `advancedRailRuntime`, `advancedRailEvidence`, `advancedRailGraphLite`; tests and JS use the same ids.
