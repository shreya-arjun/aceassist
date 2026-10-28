// Pure helpers for the voice panel, kept free of React/SDK so they're unit-testable.

const AGENT_ID_PATTERN = /^agent_[A-Za-z0-9]+$/;

// Prefer a server-issued token (works for private agents, keeps the API key on
// the backend). Fall back to a public agent ID from VITE_ELEVENLABS_AGENT_ID.
export function resolveConnection({ backendConfigured, agentId }) {
  if (backendConfigured) return { mode: "token" };
  const id = (agentId || "").trim();
  if (!id) return { mode: "none", reason: "Set VITE_ELEVENLABS_AGENT_ID in frontend/.env.local, or configure the backend keys." };
  if (!AGENT_ID_PATTERN.test(id)) return { mode: "none", reason: `"${id}" doesn't look like an agent ID (expected agent_...).` };
  return { mode: "agentId", agentId: id };
}

export function micErrorMessage(err) {
  switch (err?.name) {
    case "NotAllowedError":
    case "SecurityError":
      return "Microphone access was blocked. Allow it in your browser's site settings, then try again.";
    case "NotFoundError":
    case "OverconstrainedError":
      return "No microphone was found. Connect one and try again.";
    case "NotReadableError":
      return "Your microphone is in use by another app. Close it and try again.";
    default:
      return `Couldn't access the microphone${err?.message ? `: ${err.message}` : "."}`;
  }
}

export function hasMicrophoneApi(nav = globalThis.navigator) {
  return Boolean(nav?.mediaDevices?.getUserMedia);
}

let nextId = 0;

export function appendEntry(entries, role, text, limit = 200) {
  const clean = (text || "").trim();
  if (!clean) return entries;
  return [...entries, { id: ++nextId, role, text: clean }].slice(-limit);
}
