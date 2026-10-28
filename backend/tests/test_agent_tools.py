import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import catalog
from app.config import Settings
from app.main import create_app
from app.schemas import AppointmentRequest, CallbackRequest, InventoryQuery, SearchQuery

TOOLS_DIR = Path(__file__).resolve().parents[2] / "elevenlabs" / "tools"
TOOL_MODELS = {
    "search_rackets": SearchQuery,
    "check_inventory": InventoryQuery,
    "book_appointment": AppointmentRequest,
    "request_callback": CallbackRequest,
}


def booking(**overrides):
    body = {
        "service_type": "demo",
        "store_id": "oak-rockridge",
        "product_id": "sc-98",
        "customer_name": "Serena Park",
        "phone": "415-555-0134",
        "preferred_time": (datetime.now() + timedelta(days=3)).strftime("%Y-%m-%dT15:00"),
        "confirmed": False,
    }
    body.update(overrides)
    return body


def count_rows(db_path, table):
    with sqlite3.connect(db_path) as conn:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


# --- Envelope: always 200, explicit ok flag --------------------------------

def test_search_tool_wraps_existing_search(client):
    resp = client.post("/api/agent-tools/search_rackets",
                       json={"max_price": 200, "skill_level": "intermediate", "playing_style": "spin"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is True
    assert data["results"][0]["id"] == "sc-98"
    assert data == {"ok": True, **client.get("/api/products/search", params={
        "max_price": 200, "skill_level": "intermediate", "playing_style": "spin"}).json()}


def test_search_tool_treats_empty_optional_as_missing(client):
    resp = client.post("/api/agent-tools/search_rackets",
                       json={"max_price": "150", "skill_level": "beginner", "playing_style": ""})
    assert resp.json()["ok"] is True
    assert resp.json()["query"]["playing_style"] is None


@pytest.mark.parametrize("payload", [
    {"max_price": 150},
    {"skill_level": "beginner", "playing_style": "power"},
    {"product_name": "", "max_price": None, "skill_level": ""},
    {},
])
def test_search_tool_needs_name_or_budget_and_skill(client, payload):
    resp = client.post("/api/agent-tools/search_rackets", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["ok"] is False
    assert data["error"]["code"] == "validation_error"
    assert "product_name, or both max_price and skill_level" in data["error"]["details"]["fields"][0]["issue"]


def test_search_tool_lookup_by_name_ignores_blank_criteria(client):
    resp = client.post("/api/agent-tools/search_rackets",
                       json={"product_name": "spin craft 98", "max_price": "", "skill_level": None})
    data = resp.json()
    assert data["ok"] is True
    assert data["mode"] == "lookup"
    assert data["match_status"] == "found"
    assert [p["product_id"] for p in data["results"]] == ["sc-98"]


def test_search_tool_ambiguous_name_returns_candidates(client):
    data = client.post("/api/agent-tools/search_rackets", json={"product_name": "Velo"}).json()
    assert data["ok"] is True
    assert data["match_status"] == "ambiguous"
    assert {p["product_id"] for p in data["results"]} == {"pb-110", "sc-98"}
    assert "Ask the shopper" in data["message"]


def test_search_tool_unknown_name_does_not_guess(client):
    data = client.post("/api/agent-tools/search_rackets", json={"product_name": "Babolat Pure Drive"}).json()
    assert data["ok"] is True
    assert data["match_status"] == "not_found"
    assert data["results"] == []
    assert {p["product_id"] for p in data["catalog"]} == {p["id"] for p in catalog.PRODUCTS}


def test_looked_up_product_id_flows_into_inventory_and_booking(client, db_path):
    found = client.post("/api/agent-tools/search_rackets", json={"product_name": "SpinCraft 98"}).json()
    product_id = found["results"][0]["product_id"]

    stock = client.post("/api/agent-tools/check_inventory",
                        json={"product_id": product_id, "store_id": "oak-rockridge"}).json()
    assert stock["ok"] is True and stock["in_stock"] is True and stock["product_id"] == product_id

    booked = client.post("/api/agent-tools/book_appointment",
                         json=booking(product_id=product_id, store_id="oak-rockridge", confirmed=True)).json()
    assert booked["ok"] is True
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT product_id, store_id FROM appointments").fetchone() == (product_id, "oak-rockridge")


def test_inventory_tool_out_of_stock(client):
    resp = client.post("/api/agent-tools/check_inventory", json={"product_id": "sc-98", "store_id": "sf-mission"})
    data = resp.json()
    assert data["ok"] is True
    assert data["in_stock"] is False
    assert {s["store_id"] for s in data["other_stores_with_stock"]} == {"oak-rockridge", "sj-willow-glen"}


def test_inventory_tool_unknown_product(client):
    resp = client.post("/api/agent-tools/check_inventory", json={"product_id": "made-up", "store_id": "sf-mission"})
    assert resp.status_code == 200
    assert resp.json()["error"]["code"] == "product_not_found"


# --- Booking safeguard through the adapter ----------------------------------

def test_booking_tool_requires_confirmation_then_books(client, db_path):
    first = client.post("/api/agent-tools/book_appointment", json=booking())
    assert first.status_code == 200
    err = first.json()["error"]
    assert first.json()["ok"] is False
    assert err["code"] == "confirmation_required"
    assert "SpinCraft 98" in err["details"]["summary"]
    assert count_rows(db_path, "appointments") == 0

    second = client.post("/api/agent-tools/book_appointment", json=booking(confirmed=True))
    assert second.json()["ok"] is True
    assert second.json()["status"] == "requested"
    assert count_rows(db_path, "appointments") == 1


def test_booking_tool_demo_out_of_stock(client, db_path):
    resp = client.post("/api/agent-tools/book_appointment",
                       json=booking(store_id="sf-mission", confirmed=True))
    assert resp.json()["error"]["code"] == "demo_racket_unavailable"
    assert count_rows(db_path, "appointments") == 0


def test_booking_tool_invalid_data(client, db_path):
    resp = client.post("/api/agent-tools/book_appointment",
                       json=booking(phone="12", preferred_time="2020-01-01T10:00", confirmed=True))
    fields = {f["field"] for f in resp.json()["error"]["details"]["fields"]}
    assert fields == {"phone", "preferred_time"}
    assert count_rows(db_path, "appointments") == 0


def test_callback_tool(client, db_path):
    resp = client.post("/api/agent-tools/request_callback",
                       json={"customer_name": "Leo", "phone": "5105550199", "reason": "Grip size advice", "store_id": ""})
    assert resp.json()["ok"] is True
    assert count_rows(db_path, "callbacks") == 1


# --- Shared-secret guard -----------------------------------------------------

@pytest.fixture
def secured_client(db_path):
    settings = Settings(db_path=db_path, frontend_origin="http://localhost:5173",
                        elevenlabs_api_key=None, elevenlabs_agent_id=None, agent_tools_secret="s3cret")
    return TestClient(create_app(settings))


def test_tools_reject_missing_or_wrong_secret(secured_client):
    body = {"product_id": "sc-98", "store_id": "sf-mission"}
    assert secured_client.post("/api/agent-tools/check_inventory", json=body).status_code == 401
    wrong = secured_client.post("/api/agent-tools/check_inventory", json=body,
                                headers={"X-Agent-Tools-Secret": "nope"})
    assert wrong.status_code == 401
    assert wrong.json()["error"]["code"] == "unauthorized"


def test_tools_accept_correct_secret(secured_client):
    resp = secured_client.post("/api/agent-tools/check_inventory",
                               json={"product_id": "sc-98", "store_id": "sf-mission"},
                               headers={"X-Agent-Tools-Secret": "s3cret"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_secret_does_not_affect_demo_ui_routes(secured_client):
    assert secured_client.get("/api/stores").status_code == 200


# --- Contract: committed ElevenLabs tool configs match the backend -----------

@pytest.mark.parametrize("name", sorted(TOOL_MODELS))
def test_tool_config_matches_backend(client, name):
    config = json.loads((TOOLS_DIR / f"{name}.json").read_text())
    schema = config["api_schema"]
    body = schema["request_body_schema"]
    model_fields = TOOL_MODELS[name].model_fields

    assert config["type"] == "webhook" and config["name"] == name
    assert schema["method"] == "POST"
    assert schema["url"].endswith(f"/api/agent-tools/{name}")
    assert f"/api/agent-tools/{name}" in {r.path for r in client.app.routes}
    assert set(body["properties"]) <= set(model_fields)
    assert set(body["required"]) <= set(body["properties"])
    required_by_model = {n for n, f in model_fields.items() if f.is_required()}
    assert required_by_model <= set(body["required"])

    for prop_name, prop in body["properties"].items():
        assert prop.get("description"), f"{name}.{prop_name} needs a description for the LLM"
        if prop_name == "store_id":
            assert prop["enum"] == list(catalog.STORES)
        if prop_name == "skill_level":
            assert prop["enum"] == list(catalog.SKILL_LEVELS)
        if prop_name == "playing_style":
            assert prop["enum"] == list(catalog.PLAYING_STYLES)
