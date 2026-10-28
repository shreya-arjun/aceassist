"""Adapter routes for ElevenLabs webhook tools.

These wrap the existing shop endpoints without re-implementing them. The only
difference is the response envelope: every outcome is HTTP 200 with
`{"ok": true, ...}` or `{"ok": false, "error": {code, message, details}}`.

Why: the core API signals expected outcomes with 4xx codes (e.g. 409
confirmation_required carries the read-back summary). ElevenLabs' webhook-tool
docs don't specify how non-2xx bodies reach the LLM, so the adapters make sure
the agent always sees the structured result and can recover in conversation.
"""

import hmac
import sqlite3
from collections.abc import Callable

from fastapi import APIRouter, Body, Depends, Header, Request
from pydantic import BaseModel, ValidationError

from . import shop
from .db import get_conn
from .errors import ApiError, error_dict, validation_fields
from .schemas import AppointmentRequest, CallbackRequest, InventoryQuery, SearchQuery


def require_tool_secret(request: Request, x_agent_tools_secret: str | None = Header(None)) -> None:
    expected = request.app.state.settings.agent_tools_secret
    if expected and not hmac.compare_digest(x_agent_tools_secret or "", expected):
        raise ApiError(401, "unauthorized", "Missing or invalid X-Agent-Tools-Secret header.")


router = APIRouter(prefix="/api/agent-tools", dependencies=[Depends(require_tool_secret)])


def _run(model: type[BaseModel], payload: dict, action: Callable[[BaseModel], dict]) -> dict:
    # LLMs often send "" for optional parameters they didn't collect.
    payload = {k: v for k, v in payload.items() if v not in ("", None)}
    try:
        return {"ok": True, **action(model.model_validate(payload))}
    except ValidationError as exc:
        return {"ok": False, "error": error_dict(
            "validation_error", "Some fields are missing or invalid.", {"fields": validation_fields(exc.errors())})}
    except ApiError as exc:
        return {"ok": False, "error": error_dict(exc.code, exc.message, exc.details)}


@router.post("/search_rackets")
def search_rackets(payload: dict = Body(...)):
    return _run(SearchQuery, payload, shop.search_products)


@router.post("/check_inventory")
def check_inventory(payload: dict = Body(...)):
    return _run(InventoryQuery, payload, lambda q: shop.check_inventory(q.product_id, q.store_id))


@router.post("/book_appointment")
def book_appointment(payload: dict = Body(...), conn: sqlite3.Connection = Depends(get_conn)):
    return _run(AppointmentRequest, payload, lambda req: shop.book_appointment(req, conn))


@router.post("/request_callback")
def request_callback(payload: dict = Body(...), conn: sqlite3.Connection = Depends(get_conn)):
    return _run(CallbackRequest, payload, lambda req: shop.request_callback(req, conn))
