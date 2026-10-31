"""Pydantic schemas for product management."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.product import ProductStatus

MAX_DESCRIPTION_LENGTH = 2000


def _clean_name(value: str) -> str:
    value = value.strip()
    if not 1 <= len(value) <= 150:
        raise ValueError("Product name must be between 1 and 150 characters.")
    return value


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value or None


class ProductCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    product_type: str | None = Field(default=None, max_length=50)
    base_price: Decimal = Field(ge=0, max_digits=12, decimal_places=2)
    status: ProductStatus = ProductStatus.ACTIVE

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        return _clean_name(value)

    @field_validator("description", "product_type")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)


class ProductUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=150)
    description: str | None = Field(default=None, max_length=MAX_DESCRIPTION_LENGTH)
    product_type: str | None = Field(default=None, max_length=50)
    base_price: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        return _clean_name(value) if value is not None else None

    @field_validator("description", "product_type")
    @classmethod
    def validate_optional_text(cls, value: str | None) -> str | None:
        return _clean_optional_text(value)

    @model_validator(mode="after")
    def require_at_least_one_field(self) -> "ProductUpdate":
        if not self.model_fields_set:
            raise ValueError("Provide at least one field to update.")
        return self


class ProductStatusUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: ProductStatus


class ProductOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    product_type: str | None
    base_price: Decimal
    status: str
    created_at: datetime
    updated_at: datetime
