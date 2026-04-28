import { escapeHtml, formatApiError, parseApiError } from "/js/shared.js";

const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const menuToggle = document.getElementById("menuToggle");
const closeSidebar = document.getElementById("closeSidebar");

const provider = document.getElementById("provider");
const model = document.getElementById("model");
const baseUrl = document.getElementById("baseUrl");
const apiKey = document.getElementById("apiKey");
const runtimeSummary = document.getElementById("runtimeSummary");
const runtimeProfileMsg = document.getElementById("runtimeProfileMsg");
const appOverviewRuntime = document.getElementById("appOverviewRuntime");
const appRecoverySteps = document.getElementById("appRecoverySteps");
const appOpsBaselineMsg = document.getElementById("appOpsBaselineMsg");
const advancedSettings = document.getElementById("advancedSettings");
const advancedSettingsToggle = document.getElementById("advancedSettingsToggle");
const collection = document.getElementById("collection");
const collection2 = document.getElementById("collection2");
const collectionHint = document.getElementById("collectionHint");
const userInput = document.getElementById("userInput");

const sendBtn = document.getElementById("sendBtn");
const healthBtn = document.getElementById("healthBtn");
const reindexBtn = document.getElementById("reindexBtn");

const chatContainer = document.getElementById("chatContainer");
const statusIndicator = document.getElementById("statusIndicator");
const statusMsg = document.getElementById("statusMsg");
const docList = document.getElementById("docList");
const docTitle = document.getElementById("docTitle");
const docViewer = document.getElementById("docViewer");
const uploadSource = document.getElementById("uploadSource");
const uploadDocKey = document.getElementById("uploadDocKey");
const uploadRequestType = document.getElementById("uploadRequestType");
const uploadCountry = document.getElementById("uploadCountry");
const uploadDocType = document.getElementById("uploadDocType");
const uploadChangeSummary = document.getElementById("uploadChangeSummary");
const uploadDefaultsSummary = document.getElementById("uploadDefaultsSummary");
const uploadMetadataFields = document.getElementById("uploadMetadataFields");
const uploadMetadataToggle = document.getElementById("uploadMetadataToggle");
const uploadContent = document.getElementById("uploadContent");
const uploadBtn = document.getElementById("uploadBtn");
const uploadMsg = document.getElementById("uploadMsg");

let collectionItems = [];
let lastHealth = null;
let advancedSettingsOpen = false;
let runtimeDefaultsLoaded = false;
let uploadMetadataOpen = false;

const LAYERED_RAG_TIMEOUT_SECONDS = 60;

const offlineRecoverySteps = [
  "run_doc_rag.bat 또는 app_api.py로 서버를 다시 시작합니다.",
  "Ollama/LLM 서버와 기본 모델 준비 상태를 확인합니다.",
  "vectors=0 또는 fingerprint 문제가 보이면 Reindex를 실행합니다.",
  "/intro에서 상태를 다시 확인한 뒤 질문을 재시도합니다.",
];

function renderMarkdownBasic(markdown) {
  const lines = markdown.split("\n");
  const html = [];
  let inList = false;
  let inCode = false;
  for (const line of lines) {
    if (line.startsWith("```")) {
      if (!inCode) {
        html.push("<pre><code>");
        inCode = true;
      } else {
        html.push("</code></pre>");
        inCode = false;
      }
      continue;
    }
    if (inCode) {
      html.push(escapeHtml(line) + "\n");
      continue;
    }

    const text = escapeHtml(line);
    if (text.startsWith("#### ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push("<h4>" + text.slice(5) + "</h4>");
    } else if (text.startsWith("### ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push("<h3>" + text.slice(4) + "</h3>");
    } else if (text.startsWith("## ")) {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push("<h2>" + text.slice(3) + "</h2>");
    } else if (text.startsWith("- ")) {
      if (!inList) { html.push("<ul>"); inList = true; }
      html.push("<li>" + text.slice(2) + "</li>");
    } else if (text.trim() === "") {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push("<br>");
    } else {
      if (inList) { html.push("</ul>"); inList = false; }
      html.push("<p>" + text + "</p>");
    }
  }
  if (inList) html.push("</ul>");
  if (inCode) html.push("</code></pre>");
  return html.join("");
}

function appendMessage(role, text) {
  const message = document.createElement("div");
  message.className = "chat-message " + role;
  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = text;
  message.appendChild(body);
  chatContainer.appendChild(message);
  chatContainer.scrollTop = chatContainer.scrollHeight;
  return message;
}

function formatJsonBlock(value) {
  return escapeHtml(JSON.stringify(value || {}, null, 2));
}

function renderSourceSummary(sources) {
  if (!Array.isArray(sources) || !sources.length) {
    return "<p class='trace-empty'>source 요약이 없습니다.</p>";
  }
  return `
    <ul class="trace-source-list">
      ${sources.map((item) => `
        <li>
          <strong>${escapeHtml(item.source || "unknown")}</strong>
          <span>${escapeHtml(item.h2 || "-")}</span>
          <small>collection=${escapeHtml(item.collection_key || "-")}</small>
        </li>
      `).join("")}
    </ul>
  `;
}

function buildResponseDetails(meta) {
  if (!meta || typeof meta !== "object") return null;
  const details = document.createElement("details");
  details.className = "response-details";
  details.innerHTML = `
    <summary>실행 상세 보기</summary>
    <div class="response-detail-section">
      <p class="trace-summary">
        request_id=${escapeHtml(meta.request_id || "-")} |
        collections=${escapeHtml((meta.collections || []).join(",") || "-")} |
        route=${escapeHtml(meta.route_reason || "-")} |
        budget=${escapeHtml(meta.budget_profile || "-")}
      </p>
      <div class="trace-block">
        <h4>Source Summary</h4>
        ${renderSourceSummary(meta.sources)}
      </div>
      <div class="trace-block">
        <h4>Stage Timings</h4>
        <pre>${formatJsonBlock(meta.stage_timings || {})}</pre>
      </div>
      <div class="trace-block">
        <h4>Context Trace</h4>
        <pre>${formatJsonBlock(meta.context || {})}</pre>
      </div>
      <div class="trace-block">
        <h4>Invoke Trace</h4>
        <pre>${formatJsonBlock(meta.invoke || {})}</pre>
      </div>
    </div>
  `;
  return details;
}

function buildSupportSummary(meta) {
  if (!meta || typeof meta !== "object") return null;
  const support = document.createElement("div");
  support.className = "response-support";
  const level = meta.support_level || "insufficient_context";
  const reason = meta.support_reason || "-";
  const citations = Array.isArray(meta.citations) && meta.citations.length
    ? meta.citations.join(" | ")
    : "표시할 citation이 없습니다.";
  support.textContent = `근거 수준=${level} | reason=${reason} | citations=${citations}`;
  return support;
}

function renderBotResponse(messageNode, text, meta) {
  messageNode.replaceChildren();
  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = text;
  messageNode.appendChild(body);
  const support = buildSupportSummary(meta);
  if (support) {
    messageNode.appendChild(support);
  }
  const details = buildResponseDetails(meta);
  if (details) {
    messageNode.appendChild(details);
  }
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function renderSemanticSearchResponse(messageNode, data) {
  const results = Array.isArray(data?.results) ? data.results : [];
  messageNode.replaceChildren();

  const body = document.createElement("div");
  body.className = "message-text";
  body.textContent = results.length
    ? "빠른 시맨틱 검색 결과입니다. RAG 답변은 이어서 생성 중입니다."
    : "빠른 시맨틱 검색에서 관련 문서를 찾지 못했습니다. RAG 답변은 이어서 생성 중입니다.";
  messageNode.appendChild(body);

  const meta = data?.meta || {};
  const support = document.createElement("div");
  support.className = "response-support";
  support.textContent =
    `검색 모드=${meta.search_mode || "semantic_fallback"} | ` +
    `route=${meta.route_reason || "-"} | ` +
    `strategy=${meta.retrieval_strategy || "-"}`;
  messageNode.appendChild(support);

  if (results.length) {
    const list = document.createElement("ol");
    list.className = "semantic-result-list";
    results.forEach((item) => {
      const row = document.createElement("li");
      const title = document.createElement("strong");
      title.textContent = `${item.source || "unknown"}${item.h2 ? ` > ${item.h2}` : ""}`;
      const snippet = document.createElement("p");
      snippet.textContent = item.snippet || "";
      const metaLine = document.createElement("small");
      metaLine.textContent = `rank=${item.rank || "-"} | collection=${item.collection_key || "-"}`;
      row.appendChild(title);
      row.appendChild(snippet);
      row.appendChild(metaLine);
      list.appendChild(row);
    });
    messageNode.appendChild(list);
  }

  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function renderSemanticSearchError(messageNode, rawError, parsedError) {
  const message = rawError?.code === "VECTORSTORE_EMPTY"
    ? `${formatApiError(parsedError)} | 빠른 검색을 위해 Reindex가 필요합니다.`
    : `${formatApiError(parsedError)} | 빠른 검색은 건너뛰고 RAG 답변 생성을 계속합니다.`;
  renderBotResponse(messageNode, message, null);
}

function setStatus(type, text, detail) {
  statusIndicator.className = "status-indicator " + type;
  statusIndicator.querySelector(".status-text").textContent = text;
  statusMsg.textContent = detail || "";
}

function syncDefaults() {
  if (provider.value === "lmstudio") {
    model.value = "local-model";
    baseUrl.value = "http://localhost:1234/v1";
  } else if (provider.value === "groq") {
    model.value = "groq-model";
    baseUrl.value = "https://api.groq.com/openai/v1";
  } else if (provider.value === "ollama") {
    model.value = "llama3.1:8b";
    baseUrl.value = "http://localhost:11434";
  } else {
    model.value = "gpt-4o-mini";
    baseUrl.value = "";
  }
}

function formatRuntimeProfile(data) {
  const status = data.runtime_profile_status || "unknown";
  const scope = data.runtime_profile_scope || "-";
  const recommendation = data.runtime_profile_recommendation || "";
  const embeddingStatus = data.embedding_fingerprint_status || "-";
  const timeout = data.query_timeout_seconds ?? "-";
  const model = data.default_llm_model || "-";
  const needsAction = status !== "verified" && recommendation;
  return (
    `런타임: ${status} (${scope}) | model=${model} | timeout=${timeout}s | 인덱스=${embeddingStatus}` +
    `${needsAction ? ` | next: ${recommendation}` : ""}`
  );
}

function formatAppOverview(data) {
  const runtime = data.runtime_profile_status || "unknown";
  const embedding = data.embedding_fingerprint_status || "-";
  const vectors = data.vectors ?? "-";
  return `상태: 문서 벡터=${vectors} | 런타임=${runtime} | 인덱스=${embedding}`;
}

function renderRecoverySteps(target, steps) {
  if (!target) return;
  const items = Array.isArray(steps) && steps.length ? steps : offlineRecoverySteps;
  target.replaceChildren();
  items.forEach((step) => {
    const item = document.createElement("li");
    item.textContent = step;
    target.appendChild(item);
  });
}

function formatOpsBaseline(data) {
  const status = data.status || "unknown";
  const generatedAt = data.generated_at || "-";
  const summary = data.summary || {};
  const passRate = summary.pass_rate ?? 0;
  const score = summary.avg_weighted_score ?? 0;
  const p95 = summary.p95_latency_ms ?? 0;
  const diagnostics = Array.isArray(data.diagnostics) && data.diagnostics.length
    ? ` | diagnostics=${data.diagnostics.map((item) => item.code || "-").join(",")}`
    : "";
  const missingKeys = Array.isArray(data.missing_keys) && data.missing_keys.length
    ? ` | missing=${data.missing_keys.join(",")}`
    : "";
  return `최근 ops-baseline: ${status} | ready=${Boolean(data.ready)} | pass=${passRate} | score=${score} | p95=${p95}ms | generated=${generatedAt}${missingKeys}${diagnostics}`;
}

async function loadOpsBaselineStatus() {
  if (!appOpsBaselineMsg) return;
  try {
    const res = await fetch("/ops-baseline/latest");
    const data = await res.json();
    if (!res.ok) {
      appOpsBaselineMsg.textContent = "최근 ops-baseline 상태를 가져오지 못했습니다.";
      return;
    }
    appOpsBaselineMsg.textContent = formatOpsBaseline(data);
  } catch (error) {
    appOpsBaselineMsg.textContent = `최근 ops-baseline 상태를 가져오지 못했습니다. | ${String(error)}`;
  }
}

function collectionInfo(collectionKey) {
  return collectionItems.find((item) => item.key === collectionKey) || null;
}

function defaultUploadCountry(collectionKey) {
  const item = collectionInfo(collectionKey);
  return item?.default_country || "all";
}

function defaultUploadDocType(collectionKey) {
  const item = collectionInfo(collectionKey);
  return item?.default_doc_type || "summary";
}

function updateUploadDefaultsSummary() {
  if (!uploadDefaultsSummary) return;
  const collectionKey = collection.value || "all";
  const sourceText = uploadSource.value.trim() || "auto";
  const docKeyText = uploadDocKey.value.trim() || "auto";
  const requestTypeText = uploadRequestType.value || "auto";
  const countryText = uploadCountry.value || defaultUploadCountry(collectionKey);
  const docTypeText = uploadDocType.value || defaultUploadDocType(collectionKey);
  uploadDefaultsSummary.textContent =
    `업로드 기본값: source=${sourceText}, doc_key=${docKeyText}, request_type=${requestTypeText}, country=${countryText}, doc_type=${docTypeText}`;
}

function setUploadMetadataOpen(open) {
  uploadMetadataOpen = open;
  uploadMetadataFields.classList.toggle("hidden", !open);
  uploadMetadataToggle.textContent = open ? "메타데이터 접기" : "메타데이터 수정";
  updateUploadDefaultsSummary();
}

function setAdvancedSettingsOpen(open) {
  advancedSettingsOpen = open;
  advancedSettings.classList.toggle("hidden", !open);
  advancedSettingsToggle.textContent = open ? "고급 설정 접기" : "고급 설정 펼치기";
  if (!open && lastHealth) {
    applyRuntimeDefaults(lastHealth, true);
  }
}

function applyRuntimeDefaults(data, force = false) {
  if (!data) return;
  const runtimeProvider = data.default_llm_provider || "ollama";
  const runtimeModel = data.default_llm_model || "";
  const runtimeBaseUrl = data.default_llm_base_url || "";

  if (!force && runtimeDefaultsLoaded && advancedSettingsOpen) {
    return;
  }

  provider.value = runtimeProvider;
  model.value = runtimeModel;
  baseUrl.value = runtimeBaseUrl;
  runtimeDefaultsLoaded = true;

  if (runtimeSummary) {
    runtimeSummary.textContent = `기본 질의 설정: ${runtimeProvider} / ${runtimeModel}`;
  }
  if (runtimeProfileMsg) {
    runtimeProfileMsg.textContent = formatRuntimeProfile(data);
  }
  if (appOverviewRuntime) {
    appOverviewRuntime.textContent = formatAppOverview(data);
  }
  renderRecoverySteps(appRecoverySteps, data.release_web_steps);
}

function buildGuidedErrorMessage(rawError, parsedError) {
  const code = rawError?.code || "";
  const base = formatApiError(parsedError);
  if (code === "VECTORSTORE_EMPTY") {
    return `${base} | next: 왼쪽 메뉴에서 Reindex를 먼저 실행하세요.`;
  }
  if (code === "LLM_CONNECTION_FAILED") {
    if (provider.value === "ollama") {
      return `${base} | next: Ollama 서버와 모델 실행 상태를 확인한 뒤 다시 시도하세요.`;
    }
    if (provider.value === "lmstudio") {
      return `${base} | next: LM Studio 서버 주소와 모델 로드 상태를 확인하세요.`;
    }
    if (provider.value === "groq") {
      return `${base} | next: GROQ_API_KEY, base URL, 모델명을 확인하세요.`;
    }
    return `${base} | next: API 키와 base URL 설정을 확인하세요.`;
  }
  if (code === "LLM_TIMEOUT") {
    return `${base} | next: 위의 빠른 시맨틱 검색 결과를 먼저 확인하거나 더 짧은 질문으로 다시 시도하세요.`;
  }
  return base;
}

function collectionDisplayText(item) {
  const softPct = Math.round((item.soft_usage_ratio || 0) * 100);
  return `${item.label} (${item.key}) - vectors=${item.vectors}, soft=${softPct}%`;
}

function getSelectedCollectionKeys() {
  const values = [];
  const first = collection.value;
  const second = collection2.value;
  if (first) values.push(first);
  if (second && second !== first) values.push(second);
  return values.slice(0, 2);
}

function updateCollectionHint() {
  const selectedKeys = getSelectedCollectionKeys();
  if (!selectedKeys.length) {
    collectionHint.textContent = "컬렉션을 선택하세요.";
    return;
  }

  const selectedInfos = selectedKeys
    .map((key) => collectionItems.find((item) => item.key === key))
    .filter(Boolean);
  if (!selectedInfos.length) {
    collectionHint.textContent = "선택된 컬렉션 정보를 찾을 수 없습니다.";
    return;
  }

  const labels = selectedInfos.map((item) => `${item.label}(${item.key})`).join(", ");
  const maxHardPct = Math.max(...selectedInfos.map((item) => Math.round((item.hard_usage_ratio || 0) * 100)));
  if (selectedKeys.length === 1 && selectedKeys[0] === "all") {
    collectionHint.textContent = `선택: ${labels} | core 기본 경로 | 최대 hard-cap 사용률 ${maxHardPct}%`;
  } else {
    collectionHint.textContent = `선택: ${labels} | sample-pack 호환 경로(명시 선택) | 최대 hard-cap 사용률 ${maxHardPct}%`;
  }
  updateUploadDefaultsSummary();
}

async function loadCollections() {
  try {
    const res = await fetch("/collections");
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "컬렉션 로드 실패");
      collectionHint.textContent = formatApiError(error);
      return;
    }

    collectionItems = data.collections || [];
    if (!collectionItems.length) {
      collection.innerHTML = `<option value="all">전체 (기본)</option>`;
      collection2.innerHTML = `<option value="">사용 안 함</option>`;
      collectionHint.textContent = "컬렉션 정보가 없습니다.";
      return;
    }

    const defaultKey = data.default_collection_key || "all";
    const currentPrimary = collection.value;
    const currentSecondary = collection2.value;
    collection.innerHTML = collectionItems
      .map((item) => `<option value="${item.key}">${collectionDisplayText(item)}</option>`)
      .join("");
    collection2.innerHTML = `<option value="">사용 안 함</option>` + collectionItems
      .map((item) => `<option value="${item.key}">${collectionDisplayText(item)}</option>`)
      .join("");

    const primaryExists = collectionItems.some((item) => item.key === currentPrimary);
    const secondaryExists = collectionItems.some((item) => item.key === currentSecondary);
    collection.value = primaryExists ? currentPrimary : defaultKey;
    collection2.value = secondaryExists ? currentSecondary : "";
    if (collection2.value === collection.value) {
      collection2.value = "";
    }
    updateCollectionHint();
    updateUploadDefaultsSummary();
  } catch (error) {
    collectionHint.textContent = String(error);
  }
}

async function loadDocs() {
  try {
    const res = await fetch("/rag-docs");
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "문서 목록 로드 실패");
      docList.innerHTML = `<p class="status-msg">${escapeHtml(formatApiError(error))}</p>`;
      return;
    }
    if (!data.docs || data.docs.length === 0) {
      docList.innerHTML = "<p class='status-msg'>등록된 문서가 없습니다. Reindex 또는 업로드 요청 후 다시 확인하세요.</p>";
      return;
    }

    const items = data.docs.map((doc) => `
      <button class="doc-item-btn" data-name="${doc.name}">
        <span class="doc-name">${doc.name}</span>
        <span class="doc-meta">${doc.origin || "seed"} | ${doc.doc_key || "-"} | ${Math.round(doc.size / 1024)} KB</span>
      </button>
    `).join("");
    docList.innerHTML = items;

    docList.querySelectorAll(".doc-item-btn").forEach((button) => {
      button.addEventListener("click", () => openDoc(button.dataset.name));
    });
  } catch (error) {
    docList.innerHTML = `<p class="status-msg">오류: ${error}</p>`;
  }
}

async function openDoc(name) {
  docTitle.textContent = "Document Viewer - " + name;
  docViewer.innerHTML = "<p class='status-msg'>문서 로딩 중...</p>";
  try {
    const res = await fetch("/rag-docs/" + encodeURIComponent(name));
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "문서 조회 실패");
      docViewer.innerHTML = `<p class='status-msg'>${escapeHtml(formatApiError(error))}</p>`;
      return;
    }
    docViewer.innerHTML = renderMarkdownBasic(data.content || "");
  } catch (error) {
    docViewer.innerHTML = `<p class='status-msg'>오류: ${error}</p>`;
  }
}

async function healthCheck() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    lastHealth = data;
    if (!res.ok) {
      const error = parseApiError(data, "health check 실패");
      setStatus("error", "Error", formatApiError(error));
      if (runtimeProfileMsg) {
        runtimeProfileMsg.textContent = "런타임 프로파일 정보를 가져오지 못했습니다.";
      }
      renderRecoverySteps(appRecoverySteps, null);
      return;
    }

    applyRuntimeDefaults(data);
    await loadOpsBaselineStatus();

    if ((data.vectors ?? 0) <= 0) {
      setStatus(
        "warn",
        "Ready",
        "인덱스가 비어 있습니다. 왼쪽 메뉴의 Reindex를 먼저 실행한 뒤 질문하세요.",
      );
      return;
    }

    setStatus(
      "ok",
      "Online",
      `default=${data.collection_key ?? "all"}, vectors=${data.vectors ?? "-"}, llm=${data.default_llm_provider ?? "-"}`
    );
  } catch (err) {
    lastHealth = null;
    setStatus("error", "Offline", String(err));
    if (runtimeProfileMsg) {
      runtimeProfileMsg.textContent = "런타임 프로파일을 확인할 수 없습니다.";
    }
    renderRecoverySteps(appRecoverySteps, null);
  }
}

async function sendQuestion() {
  const question = userInput.value.trim();
  if (!question) return;

  if (lastHealth && (lastHealth.vectors ?? 0) <= 0) {
    appendMessage("bot", "인덱스가 아직 비어 있습니다. 왼쪽 메뉴에서 Reindex를 먼저 실행하세요.");
    return;
  }

  appendMessage("user", question);
  const semanticPending = appendMessage("bot", "빠른 시맨틱 검색 중...");
  const pending = appendMessage("bot", `RAG 답변 생성 중... 빠른 검색 결과를 먼저 표시하고 최대 ${LAYERED_RAG_TIMEOUT_SECONDS}초까지 기다립니다.`);
  const selectedCollections = getSelectedCollectionKeys();

  const semanticPayload = {
    query: question,
    collection: selectedCollections[0] || null,
    collections: selectedCollections.length ? selectedCollections : null,
    max_results: 3,
  };
  const payload = {
    query: question,
    llm_provider: provider.value,
    llm_model: model.value || null,
    llm_api_key: apiKey.value || null,
    llm_base_url: baseUrl.value || null,
    collection: selectedCollections[0] || null,
    collections: selectedCollections.length ? selectedCollections : null,
    timeout_seconds: LAYERED_RAG_TIMEOUT_SECONDS,
    debug: true,
  };

  const semanticSearchPromise = (async () => {
    try {
      const res = await fetch("/semantic-search", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(semanticPayload),
      });
      const data = await res.json();
      if (!res.ok) {
        const error = parseApiError(data, "빠른 검색 실패");
        renderSemanticSearchError(semanticPending, data, error);
        return;
      }
      renderSemanticSearchResponse(semanticPending, data);
    } catch (err) {
      renderBotResponse(semanticPending, "빠른 검색 오류: " + err, null);
    }
  })();

  const ragAnswerPromise = (async () => {
    try {
      const res = await fetch("/query", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) {
        const error = parseApiError(data, "요청 실패");
        renderBotResponse(pending, buildGuidedErrorMessage(data, error), null);
        return;
      }
      renderBotResponse(pending, data.answer, data.meta || null);
    } catch (err) {
      renderBotResponse(pending, "오류: " + err, null);
    }
  })();

  try {
    await Promise.allSettled([semanticSearchPromise, ragAnswerPromise]);
  } finally {
    userInput.value = "";
  }
}

async function reindex() {
  setStatus("warn", "Working", "문서 재인덱싱 중...");
  try {
    const res = await fetch("/reindex", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({reset: true, collection: collection.value || null}),
    });
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "reindex 실패");
      setStatus("error", "Error", formatApiError(error));
      return;
    }
    const collectionName = data.collection || collection.value || "all";
    const validationSummary = data.validation?.summary_text ? ` | ${data.validation.summary_text}` : "";
    setStatus("ok", "Online", `reindex 완료: collection=${collectionName}, vectors=${data.vectors}${validationSummary}`);
    appendMessage("bot", `재인덱싱 완료: collection=${collectionName}, vectors=${data.vectors}${validationSummary}`);
    await healthCheck();
    await loadDocs();
    await loadCollections();
    await loadOpsBaselineStatus();
  } catch (err) {
    setStatus("error", "Error", String(err));
  }
}

async function submitUploadRequest() {
  const content = uploadContent.value.trim();
  if (!content) {
    uploadMsg.textContent = "업로드할 Markdown 내용을 입력하세요.";
    return;
  }

  uploadMsg.textContent = "업로드 요청 생성 중...";
  const payload = {
    source_name: uploadSource.value.trim() || null,
    doc_key: uploadDocKey.value.trim() || null,
    request_type: uploadRequestType.value || null,
    collection: collection.value || null,
    country: uploadCountry.value || null,
    doc_type: uploadDocType.value || null,
    change_summary: uploadChangeSummary.value.trim() || null,
    content,
  };

  try {
    const res = await fetch("/upload-requests", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "업로드 요청 생성 실패");
      uploadMsg.textContent = formatApiError(error);
      return;
    }

    const request = data.request || {};
    const requestId = request.id || "-";
    const sourceName = request.source_name || uploadSource.value.trim() || "auto-generated";
    const requestType = request.request_type || "auto";
    const docKey = request.doc_key || uploadDocKey.value.trim() || "auto";
    const status = request.status || "pending";
    const autoApprove = data.auto_approve ? "on" : "off";
    uploadMsg.textContent = `요청 생성 완료: source=${sourceName}, doc_key=${docKey}, type=${requestType}, id=${requestId}, status=${status}, auto_approve=${autoApprove}`;
    uploadSource.value = "";
    uploadDocKey.value = "";
    uploadRequestType.value = "";
    uploadCountry.value = "";
    uploadDocType.value = "";
    uploadChangeSummary.value = "";
    uploadContent.value = "";
    setUploadMetadataOpen(false);

    if (status === "approved") {
      appendMessage("bot", `업로드 문서가 바로 반영되었습니다: ${sourceName} | doc_key=${docKey}`);
      await loadCollections();
      await loadDocs();
      await healthCheck();
      return;
    }

    if (status === "rejected") {
      const rejectedReason = request.rejected_reason
        || request.validation?.reasons?.[0]
        || "검증 실패";
      appendMessage("bot", `업로드 요청이 반려되었습니다: ${sourceName} | doc_key=${docKey} | 사유=${rejectedReason}`);
      return;
    }

    appendMessage("bot", `업로드 요청이 접수되었습니다: ${sourceName} | doc_key=${docKey} | type=${requestType} | 관리자 승인 대기`);
  } catch (error) {
    uploadMsg.textContent = String(error);
  }
}

provider.addEventListener("change", syncDefaults);
advancedSettingsToggle.addEventListener("click", () => {
  setAdvancedSettingsOpen(!advancedSettingsOpen);
});
uploadMetadataToggle.addEventListener("click", () => {
  setUploadMetadataOpen(!uploadMetadataOpen);
});
collection.addEventListener("change", () => {
  if (collection2.value === collection.value) {
    collection2.value = "";
  }
  updateCollectionHint();
  updateUploadDefaultsSummary();
});
collection2.addEventListener("change", () => {
  if (collection2.value === collection.value) {
    collection2.value = "";
  }
  updateCollectionHint();
});
uploadSource.addEventListener("input", updateUploadDefaultsSummary);
uploadDocKey.addEventListener("input", updateUploadDefaultsSummary);
uploadRequestType.addEventListener("change", updateUploadDefaultsSummary);
uploadCountry.addEventListener("change", updateUploadDefaultsSummary);
uploadDocType.addEventListener("change", updateUploadDefaultsSummary);

sendBtn.addEventListener("click", sendQuestion);
userInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    sendQuestion();
  }
});

healthBtn.addEventListener("click", healthCheck);
reindexBtn.addEventListener("click", reindex);
uploadBtn.addEventListener("click", submitUploadRequest);

menuToggle.addEventListener("click", () => {
  sidebar.classList.add("active");
  sidebarOverlay.classList.add("active");
});
closeSidebar.addEventListener("click", () => {
  sidebar.classList.remove("active");
  sidebarOverlay.classList.remove("active");
});
sidebarOverlay.addEventListener("click", () => {
  sidebar.classList.remove("active");
  sidebarOverlay.classList.remove("active");
});

setAdvancedSettingsOpen(false);
healthCheck();
loadOpsBaselineStatus();
loadCollections();
loadDocs();
setUploadMetadataOpen(false);
