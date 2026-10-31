"""Subscription plan and plan feature models."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects import mysql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base_class import Base

if TYPE_CHECKING:
    from app.models.product import Product


class BillingInterval(str, Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    YEARLY = "yearly"


class PlanStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"


class SubscriptionPlan(Base):
    __tablename__ = "subscription_plans"
    __table_args__ = (
        CheckConstraint(
            "`status` IN ('active', 'inactive')",
            name="ck_subscription_plans_status",
        ),
        CheckConstraint(
            "`billing_interval` IN ('monthly', 'quarterly', 'yearly')",
            name="ck_subscription_plans_billing_interval",
        ),
        CheckConstraint("price >= 0", name="ck_subscription_plans_price"),
        UniqueConstraint(
            "product_id",
            "name",
            "billing_interval",
            name="uq_subscription_plans_product_name_interval",
        ),
        Index("ix_subscription_plans_product_id", "product_id"),
        Index("ix_subscription_plans_status", "status"),
        Index("ix_subscription_plans_billing_interval", "billing_interval"),
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    product_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=PlanStatus.ACTIVE.value,
        server_default=PlanStatus.ACTIVE.value,
    )
    created_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6)"),
    )
    updated_at: Mapped[datetime] = mapped_column(
        mysql.DATETIME(fsp=6),
        nullable=False,
        server_default=text("CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"),
        onupdate=text("CURRENT_TIMESTAMP(6)"),
    )

    product: Mapped["Product"] = relationship(back_populates="plans")
    features: Mapped[list["PlanFeature"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="PlanFeature.sort_order",
    )

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return (
            f"<SubscriptionPlan id={self.id} name={self.name!r} "
            f"interval={self.billing_interval!r}>"
        )


class PlanFeature(Base):
    __tablename__ = "plan_features"
    __table_args__ = (
        UniqueConstraint("plan_id", "label", name="uq_plan_features_plan_label"),
        Index("ix_plan_features_plan_id", "plan_id"),
    )

    id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        primary_key=True,
        autoincrement=True,
    )
    plan_id: Mapped[int] = mapped_column(
        mysql.BIGINT(unsigned=True),
        ForeignKey("subscription_plans.id", ondelete="CASCADE"),
        nullable=False,
    )
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    sort_order: Mapped[int] = mapped_column(
        mysql.INTEGER(unsigned=True),
        nullable=False,
        default=0,
        server_default="0",
    )

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="features")

    def __repr__(self) -> str:  # pragma: no cover - debugging helper
        return f"<PlanFeature id={self.id} plan_id={self.plan_id} label={self.label!r}>"
