import { escapeHtml, formatApiError, parseApiError } from "/js/shared.js";

const refreshBtn = document.getElementById("refreshBtn");
const goUserBtn = document.getElementById("goUserBtn");
const adminCode = document.getElementById("adminCode");
const adminMsg = document.getElementById("adminMsg");
const statusFilter = document.getElementById("statusFilter");
const reasonFilter = document.getElementById("reasonFilter");
const searchFilter = document.getElementById("searchFilter");
const collectionMsg = document.getElementById("collectionMsg");
const requestMsg = document.getElementById("requestMsg");
const collectionTableWrap = document.getElementById("collectionTableWrap");
const requestTableWrap = document.getElementById("requestTableWrap");
const requestDetailMsg = document.getElementById("requestDetailMsg");
const requestDetailWrap = document.getElementById("requestDetailWrap");
const pendingMetric = document.getElementById("pendingMetric");
const approvedMetric = document.getElementById("approvedMetric");
const rejectedMetric = document.getElementById("rejectedMetric");
const collectionMetric = document.getElementById("collectionMetric");

let selectedRequestId = "";

function parseApiErrorMessage(data, fallbackMessage) {
  const error = parseApiError(data, fallbackMessage);
  return formatApiError(error);
}

function renderTextBlock(value) {
  const text = String(value || "").trim();
  if (!text) {
    return "<p class='status-msg'>-</p>";
  }
  return `<pre class="admin-text-block">${escapeHtml(text)}</pre>`;
}

function renderRequestType(item) {
  if (item.request_type === "update") {
    return "<strong style='color:#9a6700;'>update</strong>";
  }
  if (item.request_type === "create") {
    return "create";
  }
  return escapeHtml(item.request_type || "-");
}

function renderRequestDetail(item) {
  if (!item) {
    requestDetailMsg.textContent = "요청을 선택하면 상세가 표시됩니다.";
    requestDetailWrap.innerHTML = "";
    return;
  }

  const validation = item.validation || {};
  const reasons = Array.isArray(validation.reasons) && validation.reasons.length
    ? validation.reasons.map((reason) => `<li>${escapeHtml(reason)}</li>`).join("")
    : "<li>-</li>";
  const warnings = Array.isArray(validation.warnings) && validation.warnings.length
    ? validation.warnings.map((warning) => `<li>${escapeHtml(warning)}</li>`).join("")
    : "<li>-</li>";
  const activeDoc = item.active_doc || {};
  const activeState = item.active_doc_exists ? "있음" : "없음";
  const activeOrigin = activeDoc.origin || "-";
  const activeSummary = activeDoc.change_summary || "-";
  const activePreview = activeDoc.preview || "-";
  const rejectCode = item.rejected_reason_code || "-";
  const rejectNote = item.decision_note || item.rejected_reason_note || item.rejected_reason || "-";

  requestDetailMsg.textContent = `선택된 요청: ${item.id}`;
  requestDetailWrap.innerHTML = `
    <div class="admin-detail-grid">
      <div class="admin-detail-block">
        <strong>기본 정보</strong>
        <div class="admin-detail-list">
          <div>상태: ${escapeHtml(item.status || "-")}</div>
          <div>유형: ${renderRequestType(item)}</div>
          <div>컬렉션: ${escapeHtml(item.collection_key || "-")}</div>
          <div>doc_key: ${escapeHtml(item.doc_key || "-")}</div>
          <div>source_name: ${escapeHtml(item.source_name || "-")}</div>
          <div>change_summary: ${escapeHtml(item.change_summary || "-")}</div>
          <div>active_doc_exists: ${activeState}</div>
          <div>active_doc_origin: ${escapeHtml(activeOrigin)}</div>
        </div>
      </div>
      <div class="admin-detail-block">
        <strong>검증</strong>
        <div class="admin-detail-list">
          <div>usable: ${item.usable ? "true" : "false"}</div>
          <div>reasons:</div>
          <ul>${reasons}</ul>
          <div>warnings:</div>
          <ul>${warnings}</ul>
        </div>
      </div>
      <div class="admin-detail-block">
        <strong>반려 메모</strong>
        <div class="admin-detail-list">
          <div>reason_code: ${escapeHtml(rejectCode)}</div>
          <div>decision_note: ${escapeHtml(rejectNote)}</div>
        </div>
      </div>
    </div>
    <div class="admin-preview-grid">
      <div class="admin-preview-block">
        <strong>요청 미리보기</strong>
        <div class="admin-preview-box">
          ${renderTextBlock(item.content_preview || item.content || "-")}
        </div>
      </div>
      <div class="admin-preview-block">
        <strong>현재 active 문서 미리보기</strong>
        <div class="admin-preview-box">
          <div class="admin-preview-summary">active_summary: ${escapeHtml(activeSummary)}</div>
          ${renderTextBlock(activePreview)}
        </div>
      </div>
    </div>
  `;
}

function renderCollectionTable(items, defaultKey) {
  if (!Array.isArray(items) || items.length === 0) {
    collectionMetric.textContent = "0";
    collectionTableWrap.innerHTML = "<p class='status-msg'>컬렉션 정보가 없습니다.</p>";
    return;
  }

  collectionMetric.textContent = String(items.length);
  const rows = items.map((item) => {
    const isDefault = item.key === defaultKey ? " (default)" : "";
    const softPct = Math.round((item.soft_usage_ratio || 0) * 100);
    const hardPct = Math.round((item.hard_usage_ratio || 0) * 100);
    const capState = item.hard_exceeded
      ? "hard-cap 초과"
      : (item.soft_exceeded ? "soft-cap 경고" : "정상");
    return `
      <tr>
        <td>${escapeHtml(item.key + isDefault)}</td>
        <td>${escapeHtml(item.label)}</td>
        <td>${escapeHtml(item.name)}</td>
        <td class="numeric-cell">${item.vectors}</td>
        <td class="numeric-cell">${softPct}% / ${hardPct}%</td>
        <td>${escapeHtml(capState)}</td>
      </tr>
    `;
  }).join("");

  collectionTableWrap.innerHTML = `
    <table class="admin-data-table admin-collection-table">
      <thead>
        <tr>
          <th>key</th>
          <th>label</th>
          <th>collection</th>
          <th class="numeric-cell">vectors</th>
          <th class="numeric-cell">cap 사용률</th>
          <th>상태</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function requestActionButtons(item) {
  if (item.status !== "pending") return "-";
  return `
    <button class="secondary-btn req-approve-btn admin-action-btn" data-id="${item.id}">승인</button>
    <button class="secondary-btn req-reject-btn admin-action-btn" data-id="${item.id}">반려</button>
  `;
}

function renderRequestTable(items, counts) {
  const pending = counts?.pending ?? 0;
  const approved = counts?.approved ?? 0;
  const rejected = counts?.rejected ?? 0;
  pendingMetric.textContent = String(pending);
  approvedMetric.textContent = String(approved);
  rejectedMetric.textContent = String(rejected);

  if (!Array.isArray(items) || items.length === 0) {
    requestTableWrap.innerHTML = "<p class='status-msg'>요청 데이터가 없습니다.</p>";
    renderRequestDetail(null);
    return;
  }

  const rows = items.map((item) => {
    const usable = item.usable ? "true" : "false";
    const validation = item.validation || {};
    const reasons = Array.isArray(validation.reasons) ? validation.reasons.join(" | ") : "-";
    const reasonCode = item.rejected_reason_code || "-";
    const rejectedReason = item.rejected_reason || "-";
    const managedDoc = item.managed_doc || {};
    const managedVersion = managedDoc.version_id ? managedDoc.version_id.slice(0, 8) : "-";
    const rowClass = [
      item.request_type === "update" ? "admin-row-update" : "",
      item.id === selectedRequestId ? "is-selected" : "",
    ].filter(Boolean).join(" ");
    const activeDoc = item.active_doc || {};
    const activeDocText = item.active_doc_exists && activeDoc.exists
      ? `${activeDoc.origin || "-"} / ${activeDoc.source_name || "-"}`
      : "없음";
    return `
      <tr data-request-id="${item.id}" class="${rowClass}">
        <td>${escapeHtml(item.id)}</td>
        <td>${escapeHtml(item.source_name || "-")}</td>
        <td>${escapeHtml(item.doc_key || "-")}</td>
        <td>${renderRequestType(item)}</td>
        <td>${escapeHtml(activeDocText)}</td>
        <td>${escapeHtml(item.collection_key || "-")}</td>
        <td>${escapeHtml(item.status)}</td>
        <td>${usable}</td>
        <td>${escapeHtml(item.change_summary || "-")}</td>
        <td>${escapeHtml(reasonCode)}</td>
        <td>${escapeHtml(item.created_at || "-")}</td>
        <td>${escapeHtml(item.updated_at || "-")}</td>
        <td>${escapeHtml(managedVersion)}</td>
        <td>${escapeHtml(rejectedReason)}</td>
        <td>${escapeHtml(reasons)}</td>
        <td><div class="admin-action-row">${requestActionButtons(item)}</div></td>
      </tr>
    `;
  }).join("");

  requestMsg.textContent = `요청 집계: pending=${pending}, approved=${approved}, rejected=${rejected}`;

  requestTableWrap.innerHTML = `
    <table class="admin-data-table admin-request-table">
      <thead>
        <tr>
          <th>id</th>
          <th>source</th>
          <th>doc_key</th>
          <th>type</th>
          <th>active_doc</th>
          <th>collection</th>
          <th>status</th>
          <th>usable</th>
          <th>change_summary</th>
          <th>reject_code</th>
          <th>created_at</th>
          <th>updated_at</th>
          <th>managed_version</th>
          <th>rejected_reason</th>
          <th>validation_reasons</th>
          <th>actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;

  requestTableWrap.querySelectorAll(".req-approve-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      approveRequest(button.dataset.id);
    });
  });
  requestTableWrap.querySelectorAll(".req-reject-btn").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.stopPropagation();
      rejectRequest(button.dataset.id);
    });
  });
  requestTableWrap.querySelectorAll("tr[data-request-id]").forEach((row) => {
    row.addEventListener("click", () => {
      selectRequest(row.dataset.requestId, items);
    });
  });
}

function getAdminCode() {
  return adminCode.value.trim();
}

function selectRequest(requestId, items = []) {
  selectedRequestId = requestId || "";
  const request = items.find((item) => item.id === selectedRequestId) || null;
  renderRequestDetail(request);
}

async function loadCollections() {
  collectionMsg.textContent = "컬렉션 상태를 조회 중입니다.";
  try {
    const res = await fetch("/collections");
    const data = await res.json();
    if (!res.ok) {
      collectionMsg.textContent = "컬렉션 상태 조회 실패";
      return;
    }
    renderCollectionTable(data.collections || [], data.default_collection_key || "all");
    collectionMsg.textContent = `조회 완료: ${data.collections?.length || 0}개 컬렉션, auto_approve=${data.auto_approve ? "on" : "off"}`;
  } catch (error) {
    collectionMsg.textContent = String(error);
  }
}

async function loadRequests() {
  requestMsg.textContent = "요청 목록을 조회 중입니다.";
  const params = new URLSearchParams();
  if (statusFilter.value) params.set("status", statusFilter.value);
  if (reasonFilter.value.trim()) params.set("reason", reasonFilter.value.trim());
  if (searchFilter.value.trim()) params.set("q", searchFilter.value.trim());
  const suffix = params.toString() ? `?${params.toString()}` : "";
  try {
    const res = await fetch(`/upload-requests${suffix}`);
    const data = await res.json();
    if (!res.ok) {
      requestMsg.textContent = parseApiErrorMessage(data, "요청 조회 실패");
      return;
    }
    const items = data.requests || [];
    if (!selectedRequestId || !items.some((item) => item.id === selectedRequestId)) {
      const preferred = items.find((item) => item.status === "pending") || items[0] || null;
      selectedRequestId = preferred ? preferred.id : "";
    }
    renderRequestTable(items, data.counts || {});
    selectRequest(selectedRequestId, items);
  } catch (error) {
    requestMsg.textContent = String(error);
  }
}

async function approveRequest(requestId) {
  const code = getAdminCode();
  if (!code) {
    adminMsg.textContent = "관리자 코드를 먼저 입력하세요.";
    return;
  }

  adminMsg.textContent = `승인 처리 중: ${requestId}`;
  try {
    const res = await fetch(`/upload-requests/${encodeURIComponent(requestId)}/approve`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({code})
    });
    const data = await res.json();
    if (!res.ok) {
      adminMsg.textContent = parseApiErrorMessage(data, "승인 실패");
      return;
    }
    adminMsg.textContent = `승인 완료: ${requestId}`;
    await loadRequests();
    await loadCollections();
  } catch (error) {
    adminMsg.textContent = String(error);
  }
}

async function rejectRequest(requestId) {
  const code = getAdminCode();
  if (!code) {
    adminMsg.textContent = "관리자 코드를 먼저 입력하세요.";
    return;
  }

  const reasonCodeInput = prompt("반려 코드 입력 (FORMAT, DUPLICATE, CONTENT, SCOPE, VALIDATION, OTHER)", "OTHER");
  if (reasonCodeInput === null) {
    adminMsg.textContent = "반려가 취소되었습니다.";
    return;
  }
  const reasonSummary = prompt("반려 사유 요약을 입력하세요:");
  if (reasonSummary === null || !reasonSummary.trim()) {
    adminMsg.textContent = "반려 사유 요약 입력이 취소되었습니다.";
    return;
  }
  const decisionNoteInput = prompt("상세 메모가 있으면 입력하세요. 없으면 비워두세요:", reasonSummary.trim());
  if (decisionNoteInput === null) {
    adminMsg.textContent = "반려가 취소되었습니다.";
    return;
  }

  const reasonCode = reasonCodeInput.trim() || "OTHER";
  const decisionNote = decisionNoteInput.trim();

  adminMsg.textContent = `반려 처리 중: ${requestId}`;
  try {
    const res = await fetch(`/upload-requests/${encodeURIComponent(requestId)}/reject`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({
        code,
        reason_code: reasonCode,
        reason: reasonSummary.trim(),
        decision_note: decisionNote || reasonSummary.trim()
      })
    });
    const data = await res.json();
    if (!res.ok) {
      adminMsg.textContent = parseApiErrorMessage(data, "반려 실패");
      return;
    }
    adminMsg.textContent = `반려 완료: ${requestId}`;
    await loadRequests();
  } catch (error) {
    adminMsg.textContent = String(error);
  }
}

refreshBtn.addEventListener("click", async () => {
  await loadCollections();
  await loadRequests();
});
statusFilter.addEventListener("change", loadRequests);
reasonFilter.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadRequests();
  }
});
searchFilter.addEventListener("keydown", (event) => {
  if (event.key === "Enter") {
    event.preventDefault();
    loadRequests();
  }
});
goUserBtn.addEventListener("click", () => { location.href = "/app"; });

loadCollections();
loadRequests();
