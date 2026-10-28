# AceAssist

A voice shopping assistant demo for **Baseline Tennis Co.**, a fictional tennis retailer.

- **Milestone 1:** FastAPI + SQLite shopping workflow with a React demo console.
- **Milestone 2:** an ElevenLabs voice agent wired to the same workflow through webhook tools,
  with voice controls and a live transcript in the app.

A shopper can:

1. Get a racket recommendation from their budget, experience, and playing style.
2. Check whether that racket is in stock at a chosen store.
3. Request a demo or restringing appointment, which requires explicit confirmation.
4. Request a callback when the assistant can't help.

Everything runs locally **without ElevenLabs credentials**; the voice panel then explains what's
missing and the manual console works as before. The voice agent is only connected once you finish
[docs/ELEVENLABS_SETUP.md](docs/ELEVENLABS_SETUP.md) and provide a real agent ID.

## Project layout

```
backend/                    FastAPI + SQLite
  app/main.py               app factory, CORS, router wiring
  app/catalog.py            mock rackets, stores, per-store inventory
  app/shop.py               product search, inventory, appointments, callbacks
  app/agent_tools.py        ElevenLabs webhook-tool adapters over shop.py (no duplicated logic)
  app/voice.py              server-side ElevenLabs conversation token
  app/schemas.py            request validation (Pydantic)
  app/errors.py             one JSON error shape for every failure
  app/db.py                 SQLite schema + per-request connection
  tests/                    pytest: API workflow + agent-tool boundary
frontend/                   React + Vite demo console
  src/steps/                one component per workflow step
  src/voice/                voice panel (ElevenLabs React SDK) + pure helpers
  src/ApiLog.jsx            live request/response log
elevenlabs/
  system_prompt.md          agent prompt with the guardrails
  tools/*.json              webhook tool definitions (ElevenLabs format)
docs/ELEVENLABS_SETUP.md    step-by-step agent setup (dashboard steps marked)
```

## Setup and run

Requires Python 3.11+ and Node 18+.

```bash
# from the repo root
cp .env.example .env                              # optional; all values can stay blank
cp frontend/.env.example frontend/.env.local      # optional; add VITE_ELEVENLABS_AGENT_ID for voice

# Backend (terminal 1)
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Open http://localhost:5173. Interactive API docs are at http://localhost:8000/docs.
The SQLite file is created automatically at `backend/aceassist.db`.

### Environment variables

| Variable | File | Purpose |
| --- | --- | --- |
| `VITE_ELEVENLABS_AGENT_ID` | `frontend/.env.local` | Public agent ID for the voice panel. Bundled into browser code, so it must never be a key. |
| `AGENT_TOOLS_SECRET` | `.env` | Shared secret ElevenLabs tools send as `X-Agent-Tools-Secret`. Set it before tunnelling. |
| `ELEVENLABS_API_KEY`, `ELEVENLABS_AGENT_ID` | `.env` | Only for a private (auth-enabled) agent; the backend issues short-lived tokens. |
| `ACEASSIST_DB_PATH`, `FRONTEND_ORIGIN` | `.env` | Optional overrides. |

Both `.env` and `frontend/.env.local` are git-ignored.

### Checks

```bash
# Backend tests
cd backend && source .venv/bin/activate && pytest -v

# Frontend tests and production build
cd frontend && npm test && npm run build
```

## API

All errors look like `{"error": {"code": "...", "message": "...", "details": {...}}}`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/stores` | Store list |
| GET | `/api/products/search?max_price=&skill_level=&playing_style=` | Recommendations (no stock info) |
| GET | `/api/products/{product_id}/inventory?store_id=` | Stock at one store, plus alternatives if out of stock |
| POST | `/api/appointments` | Demo/restring request; needs `confirmed: true` |
| POST | `/api/callbacks` | Callback request |
| GET | `/api/voice/status` | Whether backend ElevenLabs credentials are configured |
| GET | `/api/voice/conversation-token` | Short-lived ElevenLabs WebRTC token (server-side key) |
| POST | `/api/agent-tools/{search_rackets,check_inventory,book_appointment,request_callback}` | Webhook-tool adapters (below) |

Error codes: `validation_error` (422), `store_not_found` / `product_not_found` (404),
`confirmation_required` and `demo_racket_unavailable` (409), `voice_not_configured` (503),
`voice_upstream_error` (502), and `unauthorized` (401, agent tools only).

### Agent-tool adapters

ElevenLabs' webhook-tool docs don't specify how a non-2xx response body reaches the LLM, but this
API uses 4xx for expected outcomes (the 409 `confirmation_required` carries the read-back summary).
So `/api/agent-tools/*` call the **same** `shop.py` functions and only change the envelope: always
HTTP 200 with `{"ok": true, ...}` or `{"ok": false, "error": {...}}`. They also treat `""` from the
LLM as "not provided", and require `X-Agent-Tools-Secret` when `AGENT_TOOLS_SECRET` is set.

### Guardrails

Enforced by the backend, so they hold for both the console and the voice agent:

- **No unverified stock claims.** Search results don't include availability. Only the inventory
  endpoint says `in_stock`, and a demo booking re-checks inventory before it is accepted.
- **No booking without confirmation.** A booking with `confirmed: false` (the default) validates
  everything, stores nothing, and returns `confirmation_required` with a `summary` to read back.
  Only a resend with `confirmed: true` creates the row. Bookings are *requests*: staff confirm the
  exact slot.
- **Graceful fallback.** Out-of-stock responses list other stores that have the racket, an empty
  search suggests the cheapest fitting option, and every failure path offers a callback.

Reinforced by the agent prompt ([elevenlabs/system_prompt.md](elevenlabs/system_prompt.md)): only
describe products using tool data, never invent specs or policies, and read the summary back before
the confirmed call.

## Demo script

### Manual console (no credentials needed, about 3 minutes)

1. **Recommend:** budget `200`, Intermediate, Spin. SpinCraft 98 ranks first. Select it.
2. **Out of stock:** check Mission District. It's out of stock, and the response offers Rockridge
   and Willow Glen. Click Rockridge and check again: in stock.
3. **Confirmation guardrail:** fill in the appointment form and click *Review details*. The API log
   shows `409 confirmation_required` with a read-back summary, and nothing is saved. Click
   *Yes, book it*: `201`.
4. **Validation:** try phone `555-12` or a past time and show the field-level `422`.
5. **Demo-unavailable path:** select Precision Control 95 (Advanced, Control, budget 250), choose
   Rockridge, and request a demo. You get `409 demo_racket_unavailable`; click
   *Request a callback instead*.
6. **Callback:** submit it. `201`.

Inspect stored rows: `sqlite3 backend/aceassist.db "select * from appointments; select * from callbacks;"`

### Voice (after completing the setup guide)

Click **Start conversation**, allow the microphone, and follow the spoken script in
[docs/ELEVENLABS_SETUP.md, step 8](docs/ELEVENLABS_SETUP.md#8-test-manual--dashboard-then-local).
The transcript shows both sides of the conversation; the same SQLite query confirms the booking.

## Connecting ElevenLabs

See [docs/ELEVENLABS_SETUP.md](docs/ELEVENLABS_SETUP.md). In short: run a tunnel to port 8000,
create the agent with the provided prompt, add the four webhook tools from `elevenlabs/tools/`,
pick allowlist or private-agent auth, and set `VITE_ELEVENLABS_AGENT_ID`.
