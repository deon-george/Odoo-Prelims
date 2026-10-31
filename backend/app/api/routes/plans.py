"""Subscription plan routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.subscription_plan import BillingInterval
from app.models.user import User, UserRole
from app.schemas.plan import (
    PlanCreate,
    PlanOut,
    PlanStatusUpdate,
    PlanUpdate,
)
from app.services import plan_service

router = APIRouter(prefix="/plans", tags=["plans"])

read_plans = require_roles(UserRole.ADMIN, UserRole.STAFF, UserRole.CUSTOMER)
admin_only = require_roles(UserRole.ADMIN)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Subscription plan not found.",
    )


@router.get("", response_model=list[PlanOut], summary="List subscription plans")
def list_plans(
    product_id: int | None = Query(default=None, gt=0),
    billing_interval: BillingInterval | None = Query(default=None),
    search: str | None = Query(default=None, max_length=150),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_plans),
) -> list[PlanOut]:
    is_customer = current_user.role == UserRole.CUSTOMER.value
    plans = plan_service.list_plans(
        db,
        include_inactive=include_inactive and not is_customer,
        only_active_products=is_customer,
        product_id=product_id,
        billing_interval=billing_interval,
        search=search,
    )
    return [PlanOut.model_validate(plan) for plan in plans]


@router.get("/{plan_id}", response_model=PlanOut, summary="Get a subscription plan")
def get_plan(
    plan_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_plans),
) -> PlanOut:
    is_customer = current_user.role == UserRole.CUSTOMER.value
    try:
        plan = plan_service.get_plan(
            db,
            plan_id,
            include_inactive=not is_customer,
            only_active_products=is_customer,
        )
    except plan_service.PlanNotFound as exc:
        raise _not_found() from exc
    return PlanOut.model_validate(plan)


@router.post(
    "",
    response_model=PlanOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a subscription plan (admin only)",
)
def create_plan(
    payload: PlanCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> PlanOut:
    try:
        plan = plan_service.create_plan(db, payload)
    except plan_service.PlanProductNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        ) from exc
    except plan_service.DuplicatePlan as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A plan with this name and billing interval already exists for the product.",
        ) from exc
    except plan_service.InactiveProductForPlan as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A plan cannot be active while its product is inactive.",
        ) from exc
    return PlanOut.model_validate(plan)


@router.patch(
    "/{plan_id}",
    response_model=PlanOut,
    summary="Edit a subscription plan (admin only)",
)
def update_plan(
    plan_id: int,
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> PlanOut:
    try:
        plan = plan_service.update_plan(db, plan_id, payload)
    except plan_service.PlanNotFound as exc:
        raise _not_found() from exc
    except plan_service.PlanProductNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found.",
        ) from exc
    except plan_service.DuplicatePlan as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A plan with this name and billing interval already exists for the product.",
        ) from exc
    except plan_service.InactiveProductForPlan as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A plan cannot be active while its product is inactive.",
        ) from exc
    return PlanOut.model_validate(plan)


@router.patch(
    "/{plan_id}/status",
    response_model=PlanOut,
    summary="Activate or deactivate a subscription plan (admin only)",
)
def update_plan_status(
    plan_id: int,
    payload: PlanStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> PlanOut:
    try:
        plan = plan_service.set_plan_status(db, plan_id, payload.status)
    except plan_service.PlanNotFound as exc:
        raise _not_found() from exc
    except plan_service.InactiveProductForPlan as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A plan cannot be active while its product is inactive.",
        ) from exc
    return PlanOut.model_validate(plan)
