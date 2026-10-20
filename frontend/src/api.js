// Thin client for the AceAssist backend. Every call is reported to `onCall`
// so the demo UI can show the raw request/response JSON.

export class ApiError extends Error {
  constructor(status, error) {
    super(error?.message || `Request failed (${status})`);
    this.status = status;
    this.code = error?.code || "network_error";
    this.details = error?.details || {};
  }
}

let onCall = () => {};
export const setCallListener = (fn) => {
  onCall = fn;
};

async function request(method, path, { params, body } = {}) {
  const query = params
    ? "?" + new URLSearchParams(Object.entries(params).filter(([, v]) => v !== "" && v != null))
    : "";
  const url = path + query;
  let status = 0;
  let data;
  try {
    const resp = await fetch(url, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
    status = resp.status;
    data = await resp.json();
  } catch {
    data = { error: { code: "network_error", message: "Can't reach the AceAssist backend. Is it running on :8000?" } };
  }
  onCall({ method, url, body, status, data, at: new Date() });
  if (status < 200 || status >= 300) throw new ApiError(status, data?.error);
  return data;
}

export const api = {
  stores: () => request("GET", "/api/stores"),
  searchProducts: (params) => request("GET", "/api/products/search", { params }),
  inventory: (productId, storeId) =>
    request("GET", `/api/products/${encodeURIComponent(productId)}/inventory`, { params: { store_id: storeId } }),
  bookAppointment: (body) => request("POST", "/api/appointments", { body }),
  requestCallback: (body) => request("POST", "/api/callbacks", { body }),
  voiceStatus: () => request("GET", "/api/voice/status"),
};
