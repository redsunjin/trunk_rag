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
  return `<pre style="white-space:pre-wrap;word-break:break-word;margin:0;">${escapeHtml(text)}</pre>`;
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
    <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px;">
      <div>
        <strong>기본 정보</strong>
        <div style="margin-top:6px;line-height:1.5;">
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
      <div>
        <strong>검증</strong>
        <div style="margin-top:6px;">
          <div>usable: ${item.usable ? "true" : "false"}</div>
          <div style="margin-top:6px;">reasons:</div>
          <ul style="margin:6px 0 0 18px;">${reasons}</ul>
          <div style="margin-top:6px;">warnings:</div>
          <ul style="margin:6px 0 0 18px;">${warnings}</ul>
        </div>
      </div>
      <div>
        <strong>반려 메모</strong>
        <div style="margin-top:6px;line-height:1.5;">
          <div>reason_code: ${escapeHtml(rejectCode)}</div>
          <div>decision_note: ${escapeHtml(rejectNote)}</div>
        </div>
      </div>
    </div>
    <div style="margin-top:14px;display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:12px;">
      <div>
        <strong>요청 미리보기</strong>
        <div style="margin-top:6px;padding:10px;border:1px solid #dee2e6;border-radius:8px;background:#fff;">
          ${renderTextBlock(item.content_preview || item.content || "-")}
        </div>
      </div>
      <div>
        <strong>현재 active 문서 미리보기</strong>
        <div style="margin-top:6px;padding:10px;border:1px solid #dee2e6;border-radius:8px;background:#fff;">
          <div style="margin-bottom:8px;">active_summary: ${escapeHtml(activeSummary)}</div>
          ${renderTextBlock(activePreview)}
        </div>
      </div>
    </div>
  `;
}

function renderCollectionTable(items, defaultKey) {
  if (!Array.isArray(items) || items.length === 0) {
    collectionTableWrap.innerHTML = "<p class='status-msg'>컬렉션 정보가 없습니다.</p>";
    return;
  }

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
        <td style="text-align:right;">${item.vectors}</td>
        <td style="text-align:right;">${softPct}% / ${hardPct}%</td>
        <td>${escapeHtml(capState)}</td>
      </tr>
    `;
  }).join("");

  collectionTableWrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:0.9rem;">
      <thead>
        <tr>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">key</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">label</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">collection</th>
          <th style="text-align:right;border-bottom:1px solid #dee2e6;padding:8px;">vectors</th>
          <th style="text-align:right;border-bottom:1px solid #dee2e6;padding:8px;">cap 사용률</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">상태</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;
}

function requestActionButtons(item) {
  if (item.status !== "pending") return "-";
  return `
    <button class="secondary-btn req-approve-btn" data-id="${item.id}" style="padding:4px 10px;">승인</button>
    <button class="secondary-btn req-reject-btn" data-id="${item.id}" style="padding:4px 10px;">반려</button>
  `;
}

function renderRequestTable(items, counts) {
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
    const rowStyle = item.request_type === "update" ? "background:rgba(255,193,7,0.08);" : "";
    const selectedStyle = item.id === selectedRequestId ? "box-shadow:inset 0 0 0 2px #2f6fed;" : "";
    const activeDoc = item.active_doc || {};
    const activeDocText = item.active_doc_exists && activeDoc.exists
      ? `${activeDoc.origin || "-"} / ${activeDoc.source_name || "-"}`
      : "없음";
    return `
      <tr data-request-id="${item.id}" style="cursor:pointer;${rowStyle}${selectedStyle}">
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
        <td style="display:flex;gap:6px;">${requestActionButtons(item)}</td>
      </tr>
    `;
  }).join("");

  const pending = counts?.pending ?? 0;
  const approved = counts?.approved ?? 0;
  const rejected = counts?.rejected ?? 0;
  requestMsg.textContent = `요청 집계: pending=${pending}, approved=${approved}, rejected=${rejected}`;

  requestTableWrap.innerHTML = `
    <table style="width:100%;border-collapse:collapse;font-size:0.85rem;">
      <thead>
        <tr>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">id</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">source</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">doc_key</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">type</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">active_doc</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">collection</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">status</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">usable</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">change_summary</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">reject_code</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">created_at</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">updated_at</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">managed_version</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">rejected_reason</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">validation_reasons</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">actions</th>
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
