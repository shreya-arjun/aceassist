"""Mock catalog and inventory for the fictional Baseline Tennis Co.

Inventory lives here (not in SQLite) because it stands in for a retailer's
existing inventory system that we'd integrate with, not data we own.
"""

STORES = {
    "sf-mission": {"id": "sf-mission", "name": "Baseline Tennis – Mission District", "city": "San Francisco"},
    "oak-rockridge": {"id": "oak-rockridge", "name": "Baseline Tennis – Rockridge", "city": "Oakland"},
    "sj-willow-glen": {"id": "sj-willow-glen", "name": "Baseline Tennis – Willow Glen", "city": "San Jose"},
}

SKILL_LEVELS = ("beginner", "intermediate", "advanced")
PLAYING_STYLES = ("power", "control", "all-court", "spin")

PRODUCTS = [
    {
        "id": "rk-100",
        "name": "Rally Kid 100",
        "brand": "Courtline",
        "price": 79.00,
        "skill_levels": ["beginner"],
        "playing_style": "all-court",
        "head_size_sq_in": 105,
        "weight_g": 270,
        "description": "Light, forgiving frame with a big sweet spot for new players.",
    },
    {
        "id": "pb-110",
        "name": "PowerBlade 110",
        "brand": "Velo",
        "price": 129.00,
        "skill_levels": ["beginner", "intermediate"],
        "playing_style": "power",
        "head_size_sq_in": 110,
        "weight_g": 280,
        "description": "Oversized head that adds easy depth to groundstrokes.",
    },
    {
        "id": "sc-98",
        "name": "SpinCraft 98",
        "brand": "Velo",
        "price": 189.00,
        "skill_levels": ["intermediate", "advanced"],
        "playing_style": "spin",
        "head_size_sq_in": 98,
        "weight_g": 300,
        "description": "Open string pattern built for heavy topspin.",
    },
    {
        "id": "ac-100",
        "name": "AllCourt Pro 100",
        "brand": "Courtline",
        "price": 169.00,
        "skill_levels": ["intermediate"],
        "playing_style": "all-court",
        "head_size_sq_in": 100,
        "weight_g": 295,
        "description": "Balanced frame that does a bit of everything well.",
    },
    {
        "id": "pc-95",
        "name": "Precision Control 95",
        "brand": "Apex",
        "price": 239.00,
        "skill_levels": ["advanced"],
        "playing_style": "control",
        "head_size_sq_in": 95,
        "weight_g": 315,
        "description": "Small head and dense pattern for players who generate their own pace.",
    },
    {
        "id": "tp-100",
        "name": "Tour Power 100",
        "brand": "Apex",
        "price": 219.00,
        "skill_levels": ["advanced"],
        "playing_style": "power",
        "head_size_sq_in": 100,
        "weight_g": 305,
        "description": "Stiff, stable frame for aggressive baseliners.",
    },
]

# product_id -> store_id -> units on hand
INVENTORY = {
    "rk-100": {"sf-mission": 6, "oak-rockridge": 3, "sj-willow-glen": 0},
    "pb-110": {"sf-mission": 4, "oak-rockridge": 0, "sj-willow-glen": 2},
    "sc-98": {"sf-mission": 0, "oak-rockridge": 2, "sj-willow-glen": 1},
    "ac-100": {"sf-mission": 3, "oak-rockridge": 5, "sj-willow-glen": 0},
    "pc-95": {"sf-mission": 1, "oak-rockridge": 0, "sj-willow-glen": 0},
    "tp-100": {"sf-mission": 0, "oak-rockridge": 0, "sj-willow-glen": 0},
}

_PRODUCTS_BY_ID = {p["id"]: p for p in PRODUCTS}


def get_product(product_id: str) -> dict | None:
    return _PRODUCTS_BY_ID.get(product_id)


def search_products(max_price: float, skill_level: str, playing_style: str | None) -> list[dict]:
    """Return products within budget for the skill level, exact style matches first."""
    matches = [p for p in PRODUCTS if p["price"] <= max_price and skill_level in p["skill_levels"]]
    if playing_style:
        matches.sort(key=lambda p: (p["playing_style"] != playing_style, p["price"]))
    else:
        matches.sort(key=lambda p: p["price"])
    return matches


def units_on_hand(product_id: str, store_id: str) -> int:
    return INVENTORY.get(product_id, {}).get(store_id, 0)
