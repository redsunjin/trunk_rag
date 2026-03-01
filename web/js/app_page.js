import { escapeHtml, formatApiError, parseApiError } from "/js/shared.js";

const sidebar = document.getElementById("sidebar");
const sidebarOverlay = document.getElementById("sidebarOverlay");
const menuToggle = document.getElementById("menuToggle");
const closeSidebar = document.getElementById("closeSidebar");

const provider = document.getElementById("provider");
const model = document.getElementById("model");
const baseUrl = document.getElementById("baseUrl");
const apiKey = document.getElementById("apiKey");
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
const uploadCountry = document.getElementById("uploadCountry");
const uploadDocType = document.getElementById("uploadDocType");
const uploadContent = document.getElementById("uploadContent");
const uploadBtn = document.getElementById("uploadBtn");
const uploadMsg = document.getElementById("uploadMsg");
let collectionItems = [];

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
  message.textContent = text;
  chatContainer.appendChild(message);
  chatContainer.scrollTop = chatContainer.scrollHeight;
}

function setStatus(type, text, detail) {
  statusIndicator.className = "status-indicator " + type;
  statusIndicator.querySelector(".status-text").textContent = text;
  statusMsg.textContent = detail || "";
}

function syncDefaults() {
  if (provider.value === "ollama") {
    model.value = "qwen3:4b";
    baseUrl.value = "http://localhost:11434";
  } else if (provider.value === "lmstudio") {
    model.value = "local-model";
    baseUrl.value = "http://localhost:1234/v1";
  } else {
    model.value = "gpt-4o-mini";
    baseUrl.value = "";
  }
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
  collectionHint.textContent = `선택: ${labels} | 최대 hard-cap 사용률 ${maxHardPct}%`;
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
      docList.innerHTML = "<p class='status-msg'>등록된 문서가 없습니다.</p>";
      return;
    }

    const items = data.docs.map((doc) => `
      <button class="doc-item-btn" data-name="${doc.name}">
        <span class="doc-name">${doc.name}</span>
        <span class="doc-meta">${Math.round(doc.size / 1024)} KB</span>
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

provider.addEventListener("change", syncDefaults);
collection.addEventListener("change", () => {
  if (collection2.value === collection.value) {
    collection2.value = "";
  }
  updateCollectionHint();
});
collection2.addEventListener("change", () => {
  if (collection2.value === collection.value) {
    collection2.value = "";
  }
  updateCollectionHint();
});

async function healthCheck() {
  try {
    const res = await fetch("/health");
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "health check 실패");
      setStatus("error", "Error", formatApiError(error));
      return;
    }
    setStatus("ok", "Online", `default=${data.collection_key ?? "all"}, vectors=${data.vectors ?? "-"}`);
  } catch (err) {
    setStatus("error", "Offline", String(err));
  }
}

async function sendQuestion() {
  const question = userInput.value.trim();
  if (!question) return;

  appendMessage("user", question);
  appendMessage("bot", "생성 중...");
  const pending = chatContainer.lastElementChild;
  const selectedCollections = getSelectedCollectionKeys();

  const payload = {
    query: question,
    llm_provider: provider.value,
    llm_model: model.value || null,
    llm_api_key: apiKey.value || null,
    llm_base_url: baseUrl.value || null,
    collection: selectedCollections[0] || null,
    collections: selectedCollections.length ? selectedCollections : null
  };

  try {
    const res = await fetch("/query", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "요청 실패");
      pending.textContent = formatApiError(error);
      return;
    }
    pending.textContent = data.answer;
  } catch (err) {
    pending.textContent = "오류: " + err;
  }

  userInput.value = "";
}

async function reindex() {
  setStatus("warn", "Working", "문서 재인덱싱 중...");
  try {
    const res = await fetch("/reindex", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({reset: true, collection: collection.value || null})
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
    await loadDocs();
    await loadCollections();
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
    collection: collection.value || null,
    country: uploadCountry.value || null,
    doc_type: uploadDocType.value || null,
    content
  };

  try {
    const res = await fetch("/upload-requests", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload)
    });
    const data = await res.json();
    if (!res.ok) {
      const error = parseApiError(data, "업로드 요청 생성 실패");
      uploadMsg.textContent = formatApiError(error);
      return;
    }

    const request = data.request || {};
    const requestId = request.id || "-";
    const status = request.status || "pending";
    const autoApprove = data.auto_approve ? "on" : "off";
    uploadMsg.textContent = `요청 생성 완료: id=${requestId}, status=${status}, auto_approve=${autoApprove}`;
    appendMessage("bot", `업로드 요청 생성: id=${requestId}, status=${status}`);

    if (status === "approved") {
      await loadCollections();
      await loadDocs();
    }
  } catch (error) {
    uploadMsg.textContent = String(error);
  }
}

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

healthCheck();
loadCollections();
loadDocs();
