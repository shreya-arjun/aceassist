import { afterEach, describe, expect, it, vi } from "vitest";
import { api, ApiError, setCallListener } from "./api.js";

function mockFetch(status, body) {
  globalThis.fetch = vi.fn().mockResolvedValue({ status, json: async () => body });
}

afterEach(() => {
  setCallListener(() => {});
  vi.restoreAllMocks();
});

describe("voice API boundary", () => {
  it("returns the conversation token but never shows it in the API log", async () => {
    mockFetch(200, { token: "secret-session-token" });
    const calls = [];
    setCallListener((c) => calls.push(c));

    const data = await api.conversationToken();

    expect(data.token).toBe("secret-session-token");
    expect(JSON.stringify(calls)).not.toContain("secret-session-token");
    expect(calls[0].data.token).toBe("[redacted]");
  });

  it("surfaces voice_not_configured as a structured error", async () => {
    mockFetch(503, { error: { code: "voice_not_configured", message: "Set keys", details: {} } });
    await expect(api.conversationToken()).rejects.toMatchObject({ code: "voice_not_configured", status: 503 });
  });

  it("reports an unreachable backend as network_error", async () => {
    globalThis.fetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
    const err = await api.voiceStatus().catch((e) => e);
    expect(err).toBeInstanceOf(ApiError);
    expect(err.code).toBe("network_error");
  });
});
