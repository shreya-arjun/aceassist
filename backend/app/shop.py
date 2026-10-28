"""Shopping workflow endpoints.

Each endpoint is shaped so it can be registered 1:1 as an ElevenLabs webhook
tool: flat parameters in, small structured JSON out.
"""

import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Query

from . import catalog
from .db import get_conn
from .errors import ApiError
from .schemas import AppointmentRequest, CallbackRequest, SearchQuery

router = APIRouter(prefix="/api")


def _require_store(store_id: str) -> dict:
    store = catalog.STORES.get(store_id)
    if not store:
        raise ApiError(404, "store_not_found", f"No store with id '{store_id}'.",
                       {"valid_store_ids": list(catalog.STORES)})
    return store


def _require_product(product_id: str) -> dict:
    product = catalog.get_product(product_id)
    if not product:
        raise ApiError(404, "product_not_found", f"No racket with id '{product_id}'.")
    return product


def _stores_with_stock(product_id: str, exclude: str | None = None) -> list[dict]:
    return [
        {"store_id": sid, "store_name": s["name"], "quantity": catalog.units_on_hand(product_id, sid)}
        for sid, s in catalog.STORES.items()
        if sid != exclude and catalog.units_on_hand(product_id, sid) > 0
    ]


@router.get("/stores")
def list_stores():
    return {"stores": list(catalog.STORES.values())}


@router.get("/products/search")
def search_products(query: Annotated[SearchQuery, Query()]):
    max_price, skill_level, playing_style = query.max_price, query.skill_level, query.playing_style
    results = catalog.search_products(max_price, skill_level, playing_style)
    response = {
        "query": {"max_price": max_price, "skill_level": skill_level, "playing_style": playing_style},
        "count": len(results),
        "results": results,
        # Search deliberately returns no stock info so nothing downstream can
        # imply availability without calling the inventory endpoint.
        "availability_note": "Stock is not included. Check inventory per store before saying a racket is available.",
    }
    if not results:
        cheapest = min((p for p in catalog.PRODUCTS if skill_level in p["skill_levels"]), key=lambda p: p["price"])
        response["suggestion"] = (
            f"Nothing fits that budget for a {skill_level} player. "
            f"The lowest-priced option is {cheapest['name']} at ${cheapest['price']:.2f}."
        )
    return response


@router.get("/products/{product_id}/inventory")
def check_inventory(product_id: str, store_id: str = Query()):
    product = _require_product(product_id)
    store = _require_store(store_id)
    quantity = catalog.units_on_hand(product_id, store_id)
    return {
        "product_id": product_id,
        "product_name": product["name"],
        "store_id": store_id,
        "store_name": store["name"],
        "in_stock": quantity > 0,
        "quantity": quantity,
        "other_stores_with_stock": [] if quantity > 0 else _stores_with_stock(product_id, exclude=store_id),
    }


@router.post("/appointments", status_code=201)
def book_appointment(req: AppointmentRequest, conn: sqlite3.Connection = Depends(get_conn)):
    store = _require_store(req.store_id)
    product = _require_product(req.product_id) if req.product_id else None

    if req.service_type == "demo" and catalog.units_on_hand(req.product_id, req.store_id) == 0:
        raise ApiError(409, "demo_racket_unavailable",
                       f"{product['name']} is not in stock at {store['name']}, so a demo can't be booked there.",
                       {"other_stores_with_stock": _stores_with_stock(req.product_id, exclude=req.store_id)})

    service = f"demo of the {product['name']}" if req.service_type == "demo" else "racket restringing"
    summary = (f"{service} at {store['name']} on {req.preferred_time:%A %B %d at %I:%M %p} "
               f"for {req.customer_name}, phone {req.phone}")

    if not req.confirmed:
        raise ApiError(409, "confirmation_required",
                       "Read the summary back to the shopper and resend with confirmed=true once they agree.",
                       {"summary": summary})

    cur = conn.execute(
        """INSERT INTO appointments
           (service_type, store_id, product_id, customer_name, phone, preferred_time, notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (req.service_type, req.store_id, req.product_id, req.customer_name, req.phone,
         req.preferred_time.isoformat(), req.notes),
    )
    return {
        "appointment_id": cur.lastrowid,
        "status": "requested",
        "summary": summary,
        "next_step": "The store will call to confirm the exact time slot.",
    }


@router.post("/callbacks", status_code=201)
def request_callback(req: CallbackRequest, conn: sqlite3.Connection = Depends(get_conn)):
    if req.store_id:
        _require_store(req.store_id)
    cur = conn.execute(
        "INSERT INTO callbacks (customer_name, phone, reason, store_id) VALUES (?, ?, ?, ?)",
        (req.customer_name.strip(), req.phone, req.reason.strip(), req.store_id),
    )
    return {
        "callback_id": cur.lastrowid,
        "status": "open",
        "message": "A store associate will call back within one business day.",
    }
