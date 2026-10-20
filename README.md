# AceAssist

A voice shopping assistant demo for **Baseline Tennis Co.**, a fictional tennis retailer.
Milestone 1 is the backend workflow plus a demo console. The ElevenLabs voice agent plugs in next,
calling the same endpoints as webhook tools.

A shopper can:

1. Get a racket recommendation from their budget, experience, and playing style.
2. Check whether that racket is in stock at a chosen store.
3. Request a demo or restringing appointment, which requires explicit confirmation.
4. Request a callback when the assistant can't help.

## Project layout

```
backend/                FastAPI + SQLite
  app/main.py           app factory, CORS, router wiring
  app/catalog.py        mock rackets, stores, per-store inventory
  app/shop.py           product search, inventory, appointments, callbacks
  app/voice.py          ElevenLabs seam: server-side conversation token
  app/schemas.py        request validation (Pydantic)
  app/errors.py         one JSON error shape for every failure
  app/db.py             SQLite schema + per-request connection
  tests/test_api.py     pytest suite
frontend/               React + Vite demo console
  src/steps/            one component per workflow step
  src/voice/            voice-agent panel (kept separate)
  src/ApiLog.jsx        live request/response log
```

## Setup and run

Requires Python 3.11+ and Node 18+.

```bash
# from the repo root
cp .env.example .env            # optional; voice keys can stay blank

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

### Tests

```bash
cd backend
source .venv/bin/activate
pytest -v
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
| GET | `/api/voice/status` | Whether ElevenLabs credentials are configured |
| GET | `/api/voice/conversation-token` | Short-lived ElevenLabs WebRTC token (server-side key) |

Error codes the agent should handle: `validation_error` (422), `store_not_found` / `product_not_found` (404),
`confirmation_required` and `demo_racket_unavailable` (409), and `voice_not_configured` (503) /
`voice_upstream_error` (502).

### Guardrails enforced by the backend

- **No unverified stock claims.** Search results don't include availability. Only the inventory
  endpoint says `in_stock`, and a demo booking re-checks inventory before it is accepted.
- **No booking without confirmation.** `POST /api/appointments` with `confirmed: false` (the default)
  validates everything, stores nothing, and returns `409 confirmation_required` with a `summary` to
  read back. Only a resend with `confirmed: true` creates the row. Bookings are *requests*: staff
  confirm the exact slot.
- **Graceful fallback.** Out-of-stock responses list other stores that have the racket, an empty
  search suggests the cheapest fitting option, and every failure path in the UI offers a callback.

## Demo script (about 3 minutes)

1. **Recommend:** budget `200`, Intermediate, Spin. SpinCraft 98 ranks first. Select it.
2. **Out of stock:** check Mission District. It's out of stock, and the response offers Rockridge and Willow Glen. Click Rockridge and check again: in stock.
3. **Confirmation guardrail:** fill in the appointment form and click *Review details*. The API log shows
   `409 confirmation_required` with a read-back summary, and nothing is saved. Click *Yes, book it*: `201`.
4. **Validation:** try phone `555-12` or a past time and show the field-level `422`.
5. **Demo-unavailable path:** select Precision Control 95 (Advanced, Control, budget 250), choose Rockridge,
   and request a demo. You get `409 demo_racket_unavailable`, so click *Request a callback instead*.
6. **Callback:** submit it. `201`.

Inspect stored rows: `sqlite3 backend/aceassist.db "select * from appointments; select * from callbacks;"`

## Connecting ElevenLabs (next milestone)

Based on the official docs:
[React SDK](https://elevenlabs.io/docs/agents-platform/libraries/react),
[conversation token API](https://elevenlabs.io/docs/api-reference/conversations/get-webrtc-token),
[webhook tools](https://elevenlabs.io/docs/agents-platform/customization/tools/server-tools).

1. Create an agent in the ElevenLabs dashboard and put `ELEVENLABS_API_KEY` and `ELEVENLABS_AGENT_ID` in `.env`.
   The key is only read by `backend/app/voice.py`, which calls
   `GET https://api.elevenlabs.io/v1/convai/conversation/token?agent_id=...` with the `xi-api-key` header.
2. Expose the backend publicly (for example with a tunnel) and add **webhook tools** that map 1:1 to the
   endpoints above: `search_rackets`, `check_inventory`, `book_appointment`, `request_callback`.
3. System prompt rules: only state availability from `check_inventory`; call `book_appointment` first
   without `confirmed`, read back `details.summary`, and resend with `confirmed=true` only after a clear yes;
   on any error you can't recover from, offer `request_callback`.
4. In `frontend/src/voice/`, install `@elevenlabs/react`, fetch `/api/voice/conversation-token`, and call
   `startSession({ conversationToken })` inside a `ConversationProvider`.
5. Before exposing tools publicly, add a shared-secret header check on the tool endpoints. The tools can
   send it as a secret header.
