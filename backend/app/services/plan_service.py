"""Subscription plan business logic."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.product import Product, ProductStatus
from app.models.subscription_plan import (
    BillingInterval,
    PlanFeature,
    PlanStatus,
    SubscriptionPlan,
)
from app.schemas.plan import PlanCreate, PlanUpdate


class PlanServiceError(Exception):
    """Base class for expected plan failures."""


class PlanNotFound(PlanServiceError):
    pass


class PlanProductNotFound(PlanServiceError):
    pass


class DuplicatePlan(PlanServiceError):
    pass


class InactiveProductForPlan(PlanServiceError):
    pass


def _with_relations():
    return (
        selectinload(SubscriptionPlan.features),
        joinedload(SubscriptionPlan.product),
    )


def list_plans(
    db: Session,
    *,
    include_inactive: bool = False,
    only_active_products: bool = False,
    product_id: int | None = None,
    billing_interval: BillingInterval | None = None,
    search: str | None = None,
) -> list[SubscriptionPlan]:
    stmt = select(SubscriptionPlan).options(*_with_relations())
    joined_product = False

    if not include_inactive:
        stmt = stmt.where(SubscriptionPlan.status == PlanStatus.ACTIVE.value)
    if product_id is not None:
        stmt = stmt.where(SubscriptionPlan.product_id == product_id)
    if billing_interval is not None:
        stmt = stmt.where(
            SubscriptionPlan.billing_interval == billing_interval.value
        )
    if only_active_products:
        stmt = stmt.join(Product, SubscriptionPlan.product_id == Product.id)
        stmt = stmt.where(Product.status == ProductStatus.ACTIVE.value)
        joined_product = True
    if search and search.strip():
        term = f"%{search.strip()}%"
        if not joined_product:
            stmt = stmt.join(Product, SubscriptionPlan.product_id == Product.id)
        stmt = stmt.where(
            or_(
                SubscriptionPlan.name.like(term),
                SubscriptionPlan.description.like(term),
                Product.name.like(term),
            )
        )

    return list(
        db.scalars(
            stmt.order_by(Product.name, SubscriptionPlan.name) if joined_product
            else stmt.order_by(SubscriptionPlan.name)
        )
    )


def _plan_stmt():
    return select(SubscriptionPlan).options(*_with_relations())


def get_plan(
    db: Session,
    plan_id: int,
    *,
    include_inactive: bool = True,
    only_active_products: bool = False,
) -> SubscriptionPlan:
    stmt = _plan_stmt().where(SubscriptionPlan.id == plan_id)
    if not include_inactive:
        stmt = stmt.where(SubscriptionPlan.status == PlanStatus.ACTIVE.value)
    if only_active_products:
        stmt = stmt.join(Product, SubscriptionPlan.product_id == Product.id).where(
            Product.status == ProductStatus.ACTIVE.value
        )
    plan = db.scalar(stmt)
    if plan is None:
        raise PlanNotFound()
    return plan


def _product_for_plan(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise PlanProductNotFound()
    return product


def _duplicate_exists(
    db: Session,
    *,
    product_id: int,
    name: str,
    billing_interval: str,
    exclude_id: int | None = None,
) -> bool:
    stmt = select(SubscriptionPlan.id).where(
        SubscriptionPlan.product_id == product_id,
        SubscriptionPlan.name == name,
        SubscriptionPlan.billing_interval == billing_interval,
    )
    if exclude_id is not None:
        stmt = stmt.where(SubscriptionPlan.id != exclude_id)
    return db.scalar(stmt) is not None


def _build_features(labels: list[str]) -> list[PlanFeature]:
    return [
        PlanFeature(label=label, sort_order=index)
        for index, label in enumerate(labels)
    ]


def create_plan(db: Session, payload: PlanCreate) -> SubscriptionPlan:
    product = _product_for_plan(db, payload.product_id)
    if (
        payload.status == PlanStatus.ACTIVE
        and product.status != ProductStatus.ACTIVE.value
    ):
        raise InactiveProductForPlan()
    if _duplicate_exists(
        db,
        product_id=payload.product_id,
        name=payload.name,
        billing_interval=payload.billing_interval.value,
    ):
        raise DuplicatePlan()

    plan = SubscriptionPlan(
        product_id=payload.product_id,
        name=payload.name,
        description=payload.description,
        price=payload.price,
        billing_interval=payload.billing_interval.value,
        status=payload.status.value,
        features=_build_features(payload.features),
    )
    db.add(plan)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicatePlan() from exc
    return get_plan(db, plan.id)


def update_plan(db: Session, plan_id: int, payload: PlanUpdate) -> SubscriptionPlan:
    plan = get_plan(db, plan_id)
    fields = payload.model_fields_set

    target_product_id = plan.product_id
    if "product_id" in fields and payload.product_id is not None:
        target_product_id = payload.product_id

    target_product = _product_for_plan(db, target_product_id)
    target_name = payload.name if "name" in fields and payload.name else plan.name
    target_interval = (
        payload.billing_interval.value
        if "billing_interval" in fields and payload.billing_interval is not None
        else plan.billing_interval
    )

    if _duplicate_exists(
        db,
        product_id=target_product_id,
        name=target_name,
        billing_interval=target_interval,
        exclude_id=plan.id,
    ):
        raise DuplicatePlan()

    # Edits are allowed while a product is inactive. Only *activating* a plan
    # requires the product to be active (enforced in create/set_plan_status).
    plan.product_id = target_product_id
    if "name" in fields and payload.name is not None:
        plan.name = payload.name
    if "description" in fields:
        plan.description = payload.description
    if "price" in fields and payload.price is not None:
        plan.price = payload.price
    if "billing_interval" in fields and payload.billing_interval is not None:
        plan.billing_interval = payload.billing_interval.value
    if "features" in fields and payload.features is not None:
        # Flush the deletes before inserting replacements so the
        # (plan_id, label) unique constraint is not hit mid-transaction.
        plan.features.clear()
        db.flush()
        plan.features.extend(_build_features(payload.features))

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicatePlan() from exc
    return get_plan(db, plan.id)


def set_plan_status(
    db: Session,
    plan_id: int,
    status: PlanStatus,
) -> SubscriptionPlan:
    plan = get_plan(db, plan_id)
    if status == PlanStatus.ACTIVE:
        if plan.product.status != ProductStatus.ACTIVE.value:
            raise InactiveProductForPlan()
    plan.status = status.value
    db.commit()
    return get_plan(db, plan.id)
