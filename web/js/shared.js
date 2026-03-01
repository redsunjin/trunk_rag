export function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;");
}

export function parseApiError(data, fallbackMessage) {
  if (!data || typeof data !== "object") {
    return { message: fallbackMessage, hint: "", requestId: "" };
  }
  const detailMessage =
    typeof data.detail === "string"
      ? data.detail
      : data.detail && typeof data.detail === "object"
      ? data.detail.message || JSON.stringify(data.detail)
      : "";
  const hint =
    data.hint ||
    (data.detail && typeof data.detail === "object" ? data.detail.hint || "" : "");
  return {
    message: data.message || detailMessage || fallbackMessage,
    hint,
    requestId: data.request_id || "",
  };
}

export function formatApiError(error) {
  const parts = [error.message];
  if (error.hint) parts.push(`hint: ${error.hint}`);
  if (error.requestId) parts.push(`request_id: ${error.requestId}`);
  return parts.join(" | ");
}
