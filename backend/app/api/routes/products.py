"""Product catalog routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.db.session import get_db
from app.models.product import ProductStatus
from app.models.user import User, UserRole
from app.schemas.product import (
    ProductCreate,
    ProductOut,
    ProductStatusUpdate,
    ProductUpdate,
)
from app.services import product_service

router = APIRouter(prefix="/products", tags=["products"])

read_products = require_roles(UserRole.ADMIN, UserRole.STAFF, UserRole.CUSTOMER)
admin_only = require_roles(UserRole.ADMIN)


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Product not found.",
    )


@router.get("", response_model=list[ProductOut], summary="List products")
def list_products(
    search: str | None = Query(default=None, max_length=150),
    include_inactive: bool = Query(default=False),
    db: Session = Depends(get_db),
    current_user: User = Depends(read_products),
) -> list[ProductOut]:
    # Customers may never see inactive products, regardless of the query flag.
    show_inactive = include_inactive and current_user.role != UserRole.CUSTOMER.value
    products = product_service.list_products(
        db,
        include_inactive=show_inactive,
        search=search,
    )
    return [ProductOut.model_validate(product) for product in products]


@router.get("/{product_id}", response_model=ProductOut, summary="Get a product")
def get_product(
    product_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(read_products),
) -> ProductOut:
    try:
        product = product_service.get_product(
            db,
            product_id,
            include_inactive=current_user.role != UserRole.CUSTOMER.value,
        )
    except product_service.ProductNotFound as exc:
        raise _not_found() from exc
    return ProductOut.model_validate(product)


@router.post(
    "",
    response_model=ProductOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a product (admin only)",
)
def create_product(
    payload: ProductCreate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> ProductOut:
    try:
        product = product_service.create_product(db, payload)
    except product_service.DuplicateProductName as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists.",
        ) from exc
    return ProductOut.model_validate(product)


@router.patch(
    "/{product_id}",
    response_model=ProductOut,
    summary="Edit a product (admin only)",
)
def update_product(
    product_id: int,
    payload: ProductUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> ProductOut:
    try:
        product = product_service.update_product(db, product_id, payload)
    except product_service.ProductNotFound as exc:
        raise _not_found() from exc
    except product_service.DuplicateProductName as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A product with this name already exists.",
        ) from exc
    return ProductOut.model_validate(product)


@router.patch(
    "/{product_id}/status",
    response_model=ProductOut,
    summary="Activate or deactivate a product (admin only)",
)
def update_product_status(
    product_id: int,
    payload: ProductStatusUpdate,
    db: Session = Depends(get_db),
    _: User = Depends(admin_only),
) -> ProductOut:
    try:
        product = product_service.set_product_status(db, product_id, payload.status)
    except product_service.ProductNotFound as exc:
        raise _not_found() from exc
    return ProductOut.model_validate(product)


__all__ = ["router", "ProductStatus"]
