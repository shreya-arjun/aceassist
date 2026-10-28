import { describe, expect, it } from "vitest";
import { appendEntry, hasMicrophoneApi, micErrorMessage, resolveConnection } from "./voiceConfig.js";

describe("resolveConnection", () => {
  it("prefers the backend token when the backend has credentials", () => {
    expect(resolveConnection({ backendConfigured: true, agentId: "agent_abc" })).toEqual({ mode: "token" });
  });

  it("falls back to a public agent ID", () => {
    expect(resolveConnection({ backendConfigured: false, agentId: " agent_abc123 " }))
      .toEqual({ mode: "agentId", agentId: "agent_abc123" });
  });

  it("is disabled with a reason when nothing is configured", () => {
    const result = resolveConnection({ backendConfigured: false, agentId: undefined });
    expect(result.mode).toBe("none");
    expect(result.reason).toMatch(/VITE_ELEVENLABS_AGENT_ID/);
  });

  it("rejects something that isn't an agent ID (e.g. a pasted API key)", () => {
    expect(resolveConnection({ backendConfigured: false, agentId: "sk_live_123" }).mode).toBe("none");
  });
});

describe("micErrorMessage", () => {
  it("explains a blocked permission", () => {
    expect(micErrorMessage({ name: "NotAllowedError" })).toMatch(/blocked/);
  });

  it("explains a missing device", () => {
    expect(micErrorMessage({ name: "NotFoundError" })).toMatch(/No microphone/);
  });

  it("falls back to the raw message", () => {
    expect(micErrorMessage({ name: "Weird", message: "boom" })).toMatch(/boom/);
  });
});

describe("hasMicrophoneApi", () => {
  it("detects getUserMedia support", () => {
    expect(hasMicrophoneApi({ mediaDevices: { getUserMedia() {} } })).toBe(true);
    expect(hasMicrophoneApi({})).toBe(false);
  });
});

describe("appendEntry", () => {
  it("adds trimmed lines and skips empty ones", () => {
    let entries = appendEntry([], "user", "  hi  ");
    entries = appendEntry(entries, "agent", "   ");
    expect(entries.map((e) => [e.role, e.text])).toEqual([["user", "hi"]]);
  });

  it("caps transcript length", () => {
    let entries = [];
    for (let i = 0; i < 5; i++) entries = appendEntry(entries, "agent", `m${i}`, 3);
    expect(entries.map((e) => e.text)).toEqual(["m2", "m3", "m4"]);
  });
});
