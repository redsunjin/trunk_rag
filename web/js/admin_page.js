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

function parseApiErrorMessage(data, fallbackMessage) {
  const error = parseApiError(data, fallbackMessage);
  return formatApiError(error);
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
    return;
  }

  const rows = items.map((item) => {
    const usable = item.usable ? "true" : "false";
    const validation = item.validation || {};
    const reasons = Array.isArray(validation.reasons) ? validation.reasons.join(" | ") : "-";
    const rejectedReason = item.rejected_reason || "-";
    return `
      <tr>
        <td>${escapeHtml(item.id)}</td>
        <td>${escapeHtml(item.source_name || "-")}</td>
        <td>${escapeHtml(item.collection_key || "-")}</td>
        <td>${escapeHtml(item.status)}</td>
        <td>${usable}</td>
        <td>${escapeHtml(item.created_at || "-")}</td>
        <td>${escapeHtml(item.updated_at || "-")}</td>
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
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">collection</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">status</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">usable</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">created_at</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">updated_at</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">rejected_reason</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">validation_reasons</th>
          <th style="text-align:left;border-bottom:1px solid #dee2e6;padding:8px;">actions</th>
        </tr>
      </thead>
      <tbody>${rows}</tbody>
    </table>
  `;

  requestTableWrap.querySelectorAll(".req-approve-btn").forEach((button) => {
    button.addEventListener("click", () => approveRequest(button.dataset.id));
  });
  requestTableWrap.querySelectorAll(".req-reject-btn").forEach((button) => {
    button.addEventListener("click", () => rejectRequest(button.dataset.id));
  });
}

function getAdminCode() {
  return adminCode.value.trim();
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
    renderRequestTable(data.requests || [], data.counts || {});
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

  const reason = prompt("반려 사유를 입력하세요:");
  if (!reason || !reason.trim()) {
    adminMsg.textContent = "반려 사유 입력이 취소되었습니다.";
    return;
  }

  adminMsg.textContent = `반려 처리 중: ${requestId}`;
  try {
    const res = await fetch(`/upload-requests/${encodeURIComponent(requestId)}/reject`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({code, reason: reason.trim()})
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
