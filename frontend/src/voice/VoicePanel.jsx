import { useEffect, useState } from "react";
import { api } from "../api.js";

// Voice integration seam. The app is fully usable without it.
// Next milestone: install @elevenlabs/react, fetch a token from
// GET /api/voice/conversation-token, and call startSession({ conversationToken }).
// The ElevenLabs API key stays on the backend; this component never sees it.
export default function VoicePanel() {
  const [configured, setConfigured] = useState(null);

  useEffect(() => {
    api.voiceStatus().then((d) => setConfigured(d.configured)).catch(() => setConfigured(false));
  }, []);

  return (
    <section className="voice">
      <h2>Voice assistant</h2>
      {configured === null && <p className="muted">Checking voice configuration…</p>}
      {configured === false && (
        <p className="muted">
          Voice is not configured. Add <code>ELEVENLABS_API_KEY</code> and <code>ELEVENLABS_AGENT_ID</code> to{" "}
          <code>.env</code> (backend only). The workflow below works without it.
        </p>
      )}
      {configured === true && (
        <p className="muted">
          Backend has ElevenLabs credentials. The browser voice client is the next milestone.
        </p>
      )}
    </section>
  );
}
