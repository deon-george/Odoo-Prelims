"""Product catalog business logic."""

from __future__ import annotations

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.product import Product, ProductStatus
from app.schemas.product import ProductCreate, ProductUpdate


class ProductServiceError(Exception):
    """Base class for expected product failures."""


class ProductNotFound(ProductServiceError):
    pass


class DuplicateProductName(ProductServiceError):
    pass


def list_products(
    db: Session,
    *,
    include_inactive: bool = False,
    search: str | None = None,
) -> list[Product]:
    stmt = select(Product)
    if not include_inactive:
        stmt = stmt.where(Product.status == ProductStatus.ACTIVE.value)
    if search and search.strip():
        term = f"%{search.strip()}%"
        stmt = stmt.where(
            or_(
                Product.name.like(term),
                Product.description.like(term),
                Product.product_type.like(term),
            )
        )
    return list(db.scalars(stmt.order_by(Product.name)))


def get_product(
    db: Session,
    product_id: int,
    *,
    include_inactive: bool = True,
) -> Product:
    stmt = select(Product).where(Product.id == product_id)
    if not include_inactive:
        stmt = stmt.where(Product.status == ProductStatus.ACTIVE.value)
    product = db.scalar(stmt)
    if product is None:
        raise ProductNotFound()
    return product


def _name_exists(db: Session, name: str, *, exclude_id: int | None = None) -> bool:
    stmt = select(Product.id).where(Product.name == name)
    if exclude_id is not None:
        stmt = stmt.where(Product.id != exclude_id)
    return db.scalar(stmt) is not None


def create_product(db: Session, payload: ProductCreate) -> Product:
    if _name_exists(db, payload.name):
        raise DuplicateProductName()

    product = Product(
        name=payload.name,
        description=payload.description,
        product_type=payload.product_type,
        base_price=payload.base_price,
        status=payload.status.value,
    )
    db.add(product)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateProductName() from exc
    db.refresh(product)
    return product


def update_product(db: Session, product_id: int, payload: ProductUpdate) -> Product:
    product = get_product(db, product_id)
    fields = payload.model_fields_set

    if "name" in fields and payload.name is not None:
        if _name_exists(db, payload.name, exclude_id=product.id):
            raise DuplicateProductName()
        product.name = payload.name
    if "description" in fields:
        product.description = payload.description
    if "product_type" in fields:
        product.product_type = payload.product_type
    if "base_price" in fields and payload.base_price is not None:
        product.base_price = payload.base_price

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateProductName() from exc
    db.refresh(product)
    return product


def set_product_status(
    db: Session,
    product_id: int,
    status: ProductStatus,
) -> Product:
    product = get_product(db, product_id)
    product.status = status.value
    db.commit()
    db.refresh(product)
    return product


def active_product_or_error(db: Session, product_id: int) -> Product:
    """Return an active product or raise ``ProductNotFound``."""
    return get_product(db, product_id, include_inactive=False)
