"""Pydantic schemas for subscription plans and plan features."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.subscription_plan import BillingInterval, PlanStatus

MAX_DESCRIPTION_LENGTH = 2000
MAX_FEATURES = 100
MAX_FEATURE_LENGTH = 255


def _clean_name(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 150:
        raise ValueError("Plan name must be between 1 and 150 characters.")
    return value


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


def _clean_features(values: list[str]) -> list[str]:
    if len(values) > MAX_FEATURES:
        raise ValueError(f"A plan can have at most {MAX_FEATURES} features.")

    cleaned: list[str] = []
    seen: set[str] = set()
    for value in values:
        label = value.strip()
        if not label:
            continue
        if len(label) > MAX_FEATURE_LENGTH:
            raise ValueError(
                f"Each feature must be at most {MAX_FEATURE_LENGTH} characters."
            )
        # MySQL's case-insensitive collation backs the (plan_id, label)
        # unique constraint, so de-duplicate case-insensitively too.
        key = label.casefold()
        if key not in seen:
            seen.add(key)
            cleaned.append(label)
    return cleaned


class PlanFeatureOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    label: str
    sort_order: int


class ProductSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    status: str


class PlanCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int = Field(gt=0)
    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    billing_interval: BillingInterval
    features: list[str] = Field(default_factory=list)
    status: PlanStatus = PlanStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: list[str]) -> list[str]:
        return _clean_features(value)


class PlanUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )
    billing_interval: BillingInterval | None = None
    features: list[str] | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _clean_name(value) if value is not None else None

    @field_validator("description")
    @classmethod
    def validate_description(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @field_validator("features")
    @classmethod
    def validate_features(cls, value: list[str] | None) -> list[str] | None:
        return _clean_features(value) if value is not None else None

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "PlanUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class PlanStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: PlanStatus


class PlanOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    name: str
    description: str | None
    price: Decimal
    billing_interval: str
    status: str
    features: list[PlanFeatureOut]
    product: ProductSummary
    created_at: datetime
    updated_at: datetime
