import sqlite3
from datetime import datetime, timedelta

import pytest


def future(days=2):
    return (datetime.now() + timedelta(days=days)).replace(hour=15, minute=0, second=0, microsecond=0).isoformat()


def booking(**overrides):
    body = {
        "service_type": "demo",
        "store_id": "sf-mission",
        "product_id": "pb-110",
        "customer_name": "Serena Park",
        "phone": "(415) 555-0134",
        "preferred_time": future(),
        "confirmed": True,
    }
    body.update(overrides)
    return body


def count_rows(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# --- Product search ---------------------------------------------------------

def test_search_returns_budget_and_skill_matches_with_style_first(client):
    resp = client.get("/api/products/search",
                      params={"max_price": 200, "skill_level": "intermediate", "playing_style": "spin"})
    assert resp.status_code == 200
    data = resp.json()
    ids = [p["id"] for p in data["results"]]
    assert ids[0] == "sc-98"
    assert set(ids) == {"sc-98", "pb-110", "ac-100"}
    assert all(p["price"] <= 200 for p in data["results"])
    assert all("quantity" not in p and "in_stock" not in p for p in data["results"])


def test_search_with_nothing_in_budget_suggests_cheapest(client):
    resp = client.get("/api/products/search", params={"max_price": 50, "skill_level": "advanced"})
    assert resp.status_code == 200
    assert resp.json()["count"] == 0
    assert "SpinCraft 98" in resp.json()["suggestion"]


def test_search_rejects_unknown_skill_level(client):
    resp = client.get("/api/products/search", params={"max_price": 150, "skill_level": "pro"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "validation_error"


# --- Inventory --------------------------------------------------------------

def test_inventory_in_stock(client):
    resp = client.get("/api/products/pb-110/inventory", params={"store_id": "sf-mission"})
    assert resp.status_code == 200
    assert resp.json()["in_stock"] is True
    assert resp.json()["quantity"] == 4


def test_inventory_out_of_stock_lists_other_stores(client):
    resp = client.get("/api/products/sc-98/inventory", params={"store_id": "sf-mission"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["in_stock"] is False
    assert data["quantity"] == 0
    assert {s["store_id"] for s in data["other_stores_with_stock"]} == {"oak-rockridge", "sj-willow-glen"}


def test_inventory_unknown_product(client):
    resp = client.get("/api/products/nope/inventory", params={"store_id": "sf-mission"})
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "product_not_found"


# --- Appointments -----------------------------------------------------------

def test_valid_confirmed_booking_is_stored(client, db_path):
    resp = client.post("/api/appointments", json=booking())
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] == "requested"
    assert "PowerBlade 110" in data["summary"]
    assert count_rows(db_path, "appointments") == 1


def test_unconfirmed_booking_returns_summary_and_stores_nothing(client, db_path):
    resp = client.post("/api/appointments", json=booking(confirmed=False))
    assert resp.status_code == 409
    err = resp.json()["error"]
    assert err["code"] == "confirmation_required"
    assert "PowerBlade 110" in err["details"]["summary"]
    assert count_rows(db_path, "appointments") == 0


def test_demo_for_out_of_stock_racket_is_rejected(client, db_path):
    resp = client.post("/api/appointments", json=booking(product_id="sc-98"))
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "demo_racket_unavailable"
    assert count_rows(db_path, "appointments") == 0


@pytest.mark.parametrize("overrides, bad_field", [
    ({"phone": "555-12"}, "phone"),
    ({"preferred_time": "2020-01-01T10:00:00"}, "preferred_time"),
    ({"service_type": "lessons"}, "service_type"),
    ({"customer_name": "   "}, "customer_name"),
    ({"product_id": None}, ""),  # demo without a racket fails the model-level check
])
def test_invalid_booking_data_is_rejected(client, db_path, overrides, bad_field):
    resp = client.post("/api/appointments", json=booking(**overrides))
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    assert bad_field in [f["field"] for f in err["details"]["fields"]]
    assert count_rows(db_path, "appointments") == 0


def test_booking_unknown_store(client):
    resp = client.post("/api/appointments", json=booking(store_id="nyc-soho"))
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "store_not_found"


def test_restring_does_not_need_a_product(client, db_path):
    resp = client.post("/api/appointments", json=booking(service_type="restring", product_id=None))
    assert resp.status_code == 201
    assert count_rows(db_path, "appointments") == 1


# --- Callbacks & voice ------------------------------------------------------

def test_callback_request_is_stored(client, db_path):
    resp = client.post("/api/callbacks", json={
        "customer_name": "Leo", "phone": "+1 510 555 0199", "reason": "Wants grip size advice"})
    assert resp.status_code == 201
    assert resp.json()["status"] == "open"
    assert count_rows(db_path, "callbacks") == 1


def test_voice_token_without_credentials_fails_cleanly(client):
    resp = client.get("/api/voice/conversation-token")
    assert resp.status_code == 503
    assert resp.json()["error"]["code"] == "voice_not_configured"
