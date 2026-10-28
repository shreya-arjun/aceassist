import { useEffect, useRef, useState } from "react";
import { ConversationProvider, useConversation } from "@elevenlabs/react";
import { api } from "../api.js";
import { appendEntry, hasMicrophoneApi, micErrorMessage, resolveConnection } from "./voiceConfig.js";

// The ElevenLabs API key never reaches the browser. We either get a short-lived
// token from our backend or connect to a public agent by ID.
const AGENT_ID = import.meta.env.VITE_ELEVENLABS_AGENT_ID;

export default function VoicePanel() {
  return (
    <ConversationProvider>
      <VoiceAgent />
    </ConversationProvider>
  );
}

function VoiceAgent() {
  const [connection, setConnection] = useState(null);
  const [error, setError] = useState(null);
  const [transcript, setTranscript] = useState([]);
  const [starting, setStarting] = useState(null);
  const add = (role, text) => setTranscript((t) => appendEntry(t, role, text));

  const conversation = useConversation({
    onMessage: ({ message, role }) => add(role, message),
    onError: (message) => setError(message || "The voice connection reported an error."),
    onAgentToolRequest: ({ tool_name }) => add("tool", `Calling ${tool_name}…`),
    onAgentToolResponse: ({ tool_name, is_error }) => is_error && add("tool", `${tool_name} failed`),
    onDisconnect: (details) => {
      add("system", details.reason === "error" ? `Disconnected: ${details.message}` : "Conversation ended.");
    },
  });
  const { status, isSpeaking, isMuted, setMuted } = conversation;
  const active = status === "connected" || status === "connecting";

  useEffect(() => {
    api.voiceStatus()
      .then((d) => setConnection(resolveConnection({ backendConfigured: d.configured, agentId: AGENT_ID })))
      .catch(() => setConnection(resolveConnection({ backendConfigured: false, agentId: AGENT_ID })));
  }, []);

  const start = async () => {
    setError(null);
    if (!hasMicrophoneApi()) {
      setError("This browser can't access a microphone here. Use a current browser on http://localhost.");
      return;
    }
    setStarting("Waiting for microphone…");
    try {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((t) => t.stop());
      } catch (err) {
        setError(micErrorMessage(err));
        return;
      }
      setStarting("Connecting…");
      setTranscript([]);
      if (connection.mode === "token") {
        const { token } = await api.conversationToken();
        conversation.startSession({ conversationToken: token });
      } else {
        conversation.startSession({ agentId: connection.agentId });
      }
    } catch (err) {
      setError(err.message || "Couldn't start the conversation.");
    } finally {
      setStarting(null);
    }
  };

  return (
    <section className="voice">
      <h2>Voice assistant</h2>
      {connection === null && <p className="muted">Checking voice configuration…</p>}
      {connection?.mode === "none" && (
        <p className="muted">
          Voice is not connected. {connection.reason} The manual workflow below works without it.
        </p>
      )}
      {connection && connection.mode !== "none" && (
        <>
          <div className="row">
            {active ? (
              <button onClick={() => conversation.endSession()}>End conversation</button>
            ) : (
              <button onClick={start} disabled={Boolean(starting)}>{starting || "Start conversation"}</button>
            )}
            {status === "connected" && (
              <button className="secondary" onClick={() => setMuted(!isMuted)}>{isMuted ? "Unmute" : "Mute"}</button>
            )}
            <span className={`pill pill-${status}`}>
              {status}{status === "connected" ? (isSpeaking ? " · agent speaking" : " · listening") : ""}
            </span>
            <span className="muted">via {connection.mode === "token" ? "backend token" : "public agent ID"}</span>
          </div>
          {error && <div className="error">{error}</div>}
          <Transcript entries={transcript} />
        </>
      )}
    </section>
  );
}

const LABELS = { user: "You", agent: "AceAssist", tool: "Tool", system: "" };

function Transcript({ entries }) {
  const end = useRef(null);
  useEffect(() => end.current?.scrollIntoView?.({ block: "nearest" }), [entries]);
  if (entries.length === 0) return null;
  return (
    <div className="transcript" aria-live="polite">
      {entries.map((e) => (
        <div key={e.id} className={`line line-${e.role}`}>
          {LABELS[e.role] && <strong>{LABELS[e.role]}: </strong>}
          {e.text}
        </div>
      ))}
      <div ref={end} />
    </div>
  );
}
