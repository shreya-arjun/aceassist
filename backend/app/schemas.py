import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from .catalog import PLAYING_STYLES, SKILL_LEVELS

PHONE_ALLOWED = re.compile(r"^\+?[\d\s().-]+$")


def normalize_phone(value: str) -> str:
    value = value.strip()
    digits = re.sub(r"\D", "", value)
    if not PHONE_ALLOWED.match(value) or not 10 <= len(digits) <= 15:
        raise ValueError("phone must contain 10-15 digits")
    return ("+" if value.startswith("+") else "") + digits


class SearchQuery(BaseModel):
    """Either a specific product lookup (product_name) or a recommendation (max_price + skill_level)."""

    product_name: str | None = Field(None, max_length=80, description="A racket the shopper named, e.g. SpinCraft 98.")
    max_price: float | None = Field(None, gt=0, le=2000, description="Shopper's budget in USD.")
    skill_level: Literal[SKILL_LEVELS] | None = None
    playing_style: Literal[PLAYING_STYLES] | None = None

    @field_validator("product_name")
    @classmethod
    def blank_name_is_none(cls, v: str | None) -> str | None:
        return v.strip() or None if v else None

    @model_validator(mode="after")
    def needs_name_or_criteria(self):
        if not self.product_name and (self.max_price is None or self.skill_level is None):
            raise ValueError("Provide product_name, or both max_price and skill_level.")
        return self


class InventoryQuery(BaseModel):
    product_id: str
    store_id: str


class AppointmentRequest(BaseModel):
    service_type: Literal["demo", "restring"]
    store_id: str
    product_id: str | None = Field(None, description="Required for demos; optional for restringing.")
    customer_name: str = Field(min_length=1, max_length=80)
    phone: str
    preferred_time: datetime = Field(description="ISO 8601, e.g. 2026-10-24T15:00. Naive times are store-local.")
    notes: str | None = Field(None, max_length=300)
    confirmed: bool = Field(False, description="Must be true, and only after the shopper confirmed the read-back summary.")

    @field_validator("customer_name")
    @classmethod
    def strip_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("customer_name cannot be blank")
        return v.strip()

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return normalize_phone(v)

    @field_validator("preferred_time")
    @classmethod
    def must_be_future(cls, v: datetime) -> datetime:
        if v <= datetime.now(v.tzinfo):
            raise ValueError("preferred_time must be in the future")
        return v

    @model_validator(mode="after")
    def demo_needs_product(self):
        if self.service_type == "demo" and not self.product_id:
            raise ValueError("product_id is required for a demo appointment")
        return self


class CallbackRequest(BaseModel):
    customer_name: str = Field(min_length=1, max_length=80)
    phone: str
    reason: str = Field(min_length=3, max_length=500)
    store_id: str | None = None

    @field_validator("phone")
    @classmethod
    def check_phone(cls, v: str) -> str:
        return normalize_phone(v)
