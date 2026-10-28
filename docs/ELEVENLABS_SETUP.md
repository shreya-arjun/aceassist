# Connecting AceAssist to an ElevenLabs voice agent

This guide connects the existing app to an ElevenLabs agent. Steps marked **[MANUAL – dashboard]**
are things you do in the ElevenLabs web dashboard; nothing in this repo can do them for you.
Steps marked **[LOCAL]** happen on your machine.

The voice agent is **not connected** until you finish these steps and put a real agent ID in
`frontend/.env.local`. Until then, the app shows "Voice is not connected" and the manual workflow
works as before.

Official docs used: [React SDK](https://elevenlabs.io/docs/eleven-agents/libraries/react),
[webhook tools](https://elevenlabs.io/docs/eleven-agents/customization/tools/webhook-tools),
[create tool API](https://elevenlabs.io/docs/api-reference/tools/create),
[agent authentication](https://elevenlabs.io/docs/eleven-agents/customization/authentication),
[dynamic variables](https://elevenlabs.io/docs/eleven-agents/customization/personalization/dynamic-variables).

## How it fits together

```
Browser (React)                    ElevenLabs                     Your FastAPI backend
VoicePanel ── voice (WebRTC) ──▶   Agent (LLM + voice)  ── webhook tools ──▶ /api/agent-tools/*
           ◀── transcript ───                                                  │ reuses shop.py
                                                                               ▼
                                                                         SQLite + mock catalog
```

- The **browser** only knows the agent ID. It never sees an ElevenLabs API key.
- **ElevenLabs** calls your backend when the agent uses a tool, so your backend must be reachable
  from the public internet while testing (see step 3).
- `/api/agent-tools/*` are thin adapters over the existing endpoints. They always return HTTP 200
  with `{"ok": true, ...}` or `{"ok": false, "error": {code, message, details}}` so the agent
  always sees the structured result, including the `confirmation_required` read-back summary.

## 1. Run the app locally [LOCAL]

Follow "Setup and run" in the README so the backend is on `http://localhost:8000` and the
frontend is on `http://localhost:5173`.

## 2. Create a tool secret [LOCAL]

Anyone who finds your tunnel URL could otherwise call the tool endpoints. Generate a secret:

```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

Put it in the repo-root `.env` (git-ignored) and restart the backend:

```bash
AGENT_TOOLS_SECRET=<the value you generated>
```

When set, `/api/agent-tools/*` returns `401 unauthorized` unless the request has the header
`X-Agent-Tools-Secret: <value>`. The demo UI's routes are not affected.

## 3. Expose the backend publicly [LOCAL]

ElevenLabs can't reach `localhost`. Use any HTTPS tunnel to port 8000, for example:

```bash
# Option A: Cloudflare quick tunnel (no account needed)
cloudflared tunnel --url http://localhost:8000

# Option B: ngrok (free account required)
ngrok http 8000
```

Copy the `https://...` URL it prints. Check it works (with your secret):

```bash
curl -X POST https://YOUR-TUNNEL-URL/api/agent-tools/check_inventory \
  -H "Content-Type: application/json" -H "X-Agent-Tools-Secret: <secret>" \
  -d '{"product_id": "sc-98", "store_id": "oak-rockridge"}'
```

You should see `{"ok": true, ... "in_stock": true ...}`. Quick-tunnel URLs change every time you
restart the tunnel; when that happens, update the four tool URLs in step 6.

## 4. Create the agent [MANUAL – dashboard]

1. In the ElevenLabs dashboard, open **Agents** and create a new blank agent named `AceAssist`.
2. **First message:** `Hi, I'm AceAssist from Baseline Tennis. Looking for a new racket, or need a restring?`
3. **System prompt:** paste the full contents of [`elevenlabs/system_prompt.md`](../elevenlabs/system_prompt.md).
4. **Timezone:** in the System Prompt editor, use the timezone button to set
   `America/Los_Angeles`. Per the dynamic-variables docs, the agent only receives the current
   date and time when a timezone is set, and it needs that to turn "Saturday at 3" into
   `2026-11-07T15:00`.
5. **LLM:** choose a high-capability model; the webhook-tools docs warn that weaker models struggle
   with tool parameters.
6. Copy the **agent ID** (starts with `agent_`).

## 5. Store the secret in ElevenLabs [MANUAL – dashboard]

Create a workspace secret (the webhook-tools docs: add a header, choose **Secret** as the header
type, then **Create New Secret**). Name it `aceassist_tools_secret` and paste the same value as
`AGENT_TOOLS_SECRET`.

## 6. Add the four webhook tools [MANUAL – dashboard]

The tool definitions live in [`elevenlabs/tools/`](../elevenlabs/tools/) in the documented
`webhook` format. A backend test (`test_tool_config_matches_backend`) checks that they match the
real routes, request models, and catalog values.

For each file (`search_rackets`, `check_inventory`, `book_appointment`, `request_callback`), on the
agent's **Tools** section choose **Add tool → Webhook** and enter:

| Field | Value |
| --- | --- |
| Name / Description | `name` and `description` from the JSON file, verbatim |
| Method | `POST` |
| URL | `https://YOUR-TUNNEL-URL/api/agent-tools/<tool name>` |
| Header | `X-Agent-Tools-Secret`, type **Secret**, value `aceassist_tools_secret` |
| Body parameters | one per entry in `request_body_schema.properties`: same identifier, type, description, and enum values; mark the ones in `required` as required |

Keep the descriptions as written. They carry the guardrails ("ONLY source of truth for
availability", "confirmed=false on the first call").

**Alternative: CLI.** The webhook-tools docs show
`elevenlabs tools add "<name>" --type "webhook" --config-path <file>`. Copy the JSON files into
`elevenlabs/local/` (git-ignored), replace `YOUR-PUBLIC-BACKEND-URL` and
`REPLACE_WITH_YOUR_SECRET_ID` there, and add them from that folder so your tunnel URL and secret ID
don't get committed.

## 7. Choose how the browser authenticates [MANUAL – dashboard + LOCAL]

The agent-authentication docs say to pick **one** method per agent:

**Option A: public agent with an allowlist (simplest).**
1. [MANUAL] In the agent's **Security** tab, add `localhost:5173` to the allowlist. Matching is
   exact on host and port; if Vite says it's using another port, add that one too.
2. [LOCAL] Create `frontend/.env.local` (git-ignored) and restart `npm run dev`:
   ```bash
   VITE_ELEVENLABS_AGENT_ID=agent_xxxxxxxxxxxx
   ```

**Option B: private agent (enable authentication).**
1. [MANUAL] Enable authentication on the agent.
2. [LOCAL] In the repo-root `.env`, set `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID`, and restart
   the backend. The voice panel then fetches a short-lived token from
   `GET /api/voice/conversation-token`; the key stays on the server.

If both are configured, the frontend uses the backend token (option B).

## 8. Test [MANUAL – dashboard, then LOCAL]

1. Use the dashboard's built-in test call first. That isolates agent/tool problems from frontend ones.
2. Then open the app, click **Start conversation**, allow the microphone, and run the script below.

Demo script (shows each safeguard):

1. "I'm an intermediate player, about 200 dollars, I like hitting with spin."
   The agent calls `search_rackets` and recommends SpinCraft 98 using catalog facts only.
2. "Is it in stock at the Mission store?"
   The agent calls `check_inventory`: out of stock, and it offers Rockridge or Willow Glen.
3. "Book me a demo at Rockridge Saturday at 3. I'm Serena, 415 555 0134."
   The agent calls `book_appointment` with `confirmed=false`, reads back the summary, and asks
   for confirmation. Nothing is saved yet.
4. "Yes." The second call uses `confirmed=true` and the booking is saved. Verify:
   `sqlite3 backend/aceassist.db "select * from appointments;"`
5. "What string tension do pros use?" The tools don't know, so the agent should offer
   `request_callback` instead of inventing an answer.

The transcript shows "Calling <tool>…" lines when ElevenLabs sends tool events to the client. If
those lines don't appear, the conversation still works; check the agent's client-event settings
in the dashboard.

## Troubleshooting

| Symptom | Likely cause |
| --- | --- |
| Panel says "Voice is not connected" | `VITE_ELEVENLABS_AGENT_ID` missing or not `agent_...`, and backend keys unset. Restart `npm run dev` after editing `.env.local`. |
| Red error "Agent not found" | Wrong agent ID. |
| Connection rejected right away | Allowlist doesn't include the exact `host:port`, or the agent has authentication enabled but you're using option A. |
| "Microphone access was blocked" | Allow the mic for `localhost` in browser site settings. |
| Agent says the tool failed / 401 in backend logs | Secret header value doesn't match `AGENT_TOOLS_SECRET`. |
| Tool calls time out | Tunnel stopped or its URL changed; update the tool URLs. |
