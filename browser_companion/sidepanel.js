const DEFAULT_SERVER_URL = "http://127.0.0.1:8000";
const MAX_PAGE_TEXT_CHARS = 6000;

const refs = {
  serverUrl: document.getElementById("serverUrl"),
  saveServerBtn: document.getElementById("saveServerBtn"),
  healthBtn: document.getElementById("healthBtn"),
  statusDot: document.getElementById("statusDot"),
  statusText: document.getElementById("statusText"),
  serverMeta: document.getElementById("serverMeta"),
  capturePageBtn: document.getElementById("capturePageBtn"),
  pageSummary: document.getElementById("pageSummary"),
  uploadDraftBtn: document.getElementById("uploadDraftBtn"),
  qualityMode: document.getElementById("qualityMode"),
  questionInput: document.getElementById("questionInput"),
  askBtn: document.getElementById("askBtn"),
  resultPanel: document.getElementById("resultPanel"),
};

let pageContext = null;

function normalizeServerUrl(value) {
  const trimmed = String(value || "").trim().replace(/\/+$/, "");
  return trimmed || DEFAULT_SERVER_URL;
}

function storageGet(key) {
  if (!globalThis.chrome?.storage?.local) return Promise.resolve({});
  return chrome.storage.local.get(key);
}

function storageSet(value) {
  if (!globalThis.chrome?.storage?.local) return Promise.resolve();
  return chrome.storage.local.set(value);
}

function setStatus(kind, message) {
  refs.statusDot.className = `status-dot ${kind === "ok" ? "ok" : kind === "error" ? "error" : ""}`;
  refs.statusText.textContent = message;
}

function setServerMeta(data = null) {
  if (!data) {
    refs.serverMeta.textContent = "server profile=-";
    return;
  }
  refs.serverMeta.textContent = [
    `model=${data.default_llm_model ?? "-"}`,
    `runtime=${data.runtime_profile_status ?? "-"}`,
    `timeout=${data.query_timeout_seconds ?? "-"}s`,
    `vectors=${data.vectors ?? "-"}`,
  ].join(" | ");
}

function showResult(text, meta = "") {
  refs.resultPanel.classList.add("visible");
  refs.resultPanel.textContent = text;
  if (meta) {
    const metaNode = document.createElement("div");
    metaNode.className = "result-meta";
    metaNode.textContent = meta;
    refs.resultPanel.appendChild(metaNode);
  }
}

function getServerUrl() {
  return normalizeServerUrl(refs.serverUrl.value);
}

async function apiFetch(path, options = {}) {
  const response = await fetch(`${getServerUrl()}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
  });
  const text = await response.text();
  let data = {};
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = {detail: text};
  }
  if (!response.ok) {
    const message = data.message || data.detail || `HTTP ${response.status}`;
    throw new Error(message);
  }
  return data;
}

function graphLiteSummary(meta) {
  const graphLite = meta?.context?.graph_lite;
  if (!graphLite || typeof graphLite !== "object") return "graph-lite=not-reported";
  const status = graphLite.status || (graphLite.enabled ? "not_run" : "disabled");
  const parts = [`graph-lite=${status}`];
  if (typeof graphLite.relation_count === "number") {
    parts.push(`relations=${graphLite.relation_count}`);
  }
  if (graphLite.context_added === true) {
    parts.push("context=added");
  }
  if (graphLite.fallback_reason) {
    parts.push(`fallback=${graphLite.fallback_reason}`);
  }
  return parts.join(" | ");
}

async function checkHealth() {
  try {
    const data = await apiFetch("/health");
    setStatus("ok", "Online");
    setServerMeta(data);
  } catch (error) {
    setStatus("error", `Disconnected | ${error.message}`);
    setServerMeta();
  }
}

async function saveServerUrl() {
  refs.serverUrl.value = getServerUrl();
  await storageSet({serverUrl: refs.serverUrl.value});
  await checkHealth();
}

async function getActivePageContext() {
  if (!globalThis.chrome?.tabs || !globalThis.chrome?.scripting) {
    throw new Error("Chrome extension API is not available.");
  }
  const [tab] = await chrome.tabs.query({active: true, currentWindow: true});
  if (!tab?.id) throw new Error("활성 탭을 찾을 수 없습니다.");
  const [result] = await chrome.scripting.executeScript({
    target: {tabId: tab.id},
    func: (maxChars) => {
      const selection = String(window.getSelection?.() || "").trim();
      const title = document.title || "";
      const url = location.href;
      const text = selection || document.body?.innerText || "";
      return {
        title,
        url,
        selection,
        text: text.replace(/\s+/g, " ").trim().slice(0, maxChars),
      };
    },
    args: [MAX_PAGE_TEXT_CHARS],
  });
  return result?.result;
}

async function capturePage() {
  try {
    pageContext = await getActivePageContext();
    const label = pageContext.selection ? "selection" : "page";
    refs.pageSummary.textContent = `${label}: ${pageContext.title || pageContext.url || "untitled"} (${pageContext.text.length} chars)`;
    refs.uploadDraftBtn.disabled = !pageContext.text;
  } catch (error) {
    pageContext = null;
    refs.uploadDraftBtn.disabled = true;
    refs.pageSummary.textContent = `Capture failed: ${error.message}`;
  }
}

async function uploadDraft() {
  if (!pageContext?.text) return;
  const sourceName = `${new URL(pageContext.url).hostname || "browser-page"}.md`;
  const content = [
    `# ${pageContext.title || "Browser page capture"}`,
    "",
    `source: ${pageContext.url}`,
    "",
    pageContext.text,
  ].join("\n");
  try {
    const data = await apiFetch("/upload-requests", {
      method: "POST",
      body: JSON.stringify({
        source_name: sourceName,
        request_type: "create",
        change_summary: "Browser companion page capture draft",
        content,
      }),
    });
    showResult(`Upload draft created for admin review: ${data.request?.id || "-"} (${data.request?.status || "-"})`);
  } catch (error) {
    showResult(`Upload draft failed: ${error.message}`);
  }
}

async function askLocalRag() {
  const query = refs.questionInput.value.trim();
  if (!query) return;
  const qualityMode = refs.qualityMode.value;
  refs.askBtn.disabled = true;
  showResult("질의 중...");
  try {
    const data = await apiFetch("/query", {
      method: "POST",
      body: JSON.stringify({
        query,
        quality_mode: qualityMode,
        quality_stage: qualityMode === "quality" ? "quality" : "balanced",
        timeout_seconds: qualityMode === "quality" ? 120 : 60,
        debug: true,
      }),
    });
    const meta = data.meta || {};
    const citations = Array.isArray(meta.citations) && meta.citations.length
      ? meta.citations.join(" | ")
      : "citations=-";
    const metaText = [
      `request_id=${meta.request_id || "-"}`,
      `model=${data.model || "-"}`,
      `support=${meta.support_level || "-"}`,
      citations,
      graphLiteSummary(meta),
    ].join(" | ");
    showResult(data.answer || "(empty answer)", metaText);
  } catch (error) {
    showResult(`Query failed: ${error.message}`);
  } finally {
    refs.askBtn.disabled = false;
  }
}

async function init() {
  const stored = await storageGet("serverUrl");
  refs.serverUrl.value = normalizeServerUrl(stored.serverUrl || DEFAULT_SERVER_URL);
  refs.saveServerBtn.addEventListener("click", saveServerUrl);
  refs.healthBtn.addEventListener("click", checkHealth);
  refs.capturePageBtn.addEventListener("click", capturePage);
  refs.uploadDraftBtn.addEventListener("click", uploadDraft);
  refs.askBtn.addEventListener("click", askLocalRag);
  await checkHealth();
}

init().catch((error) => setStatus("error", error.message));
