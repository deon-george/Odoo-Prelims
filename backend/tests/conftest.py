"""Pytest fixtures.

The test suite runs against TEST_DATABASE_URL. Environment variables are set
before importing the application so the SQLAlchemy engine binds to the test
database, never the development database.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from uuid import uuid4

from dotenv import dotenv_values

BACKEND_DIR = Path(__file__).resolve().parents[1]
_DOTENV = dotenv_values(BACKEND_DIR / ".env")

_TEST_DATABASE_URL = os.environ.get("TEST_DATABASE_URL") or _DOTENV.get(
    "TEST_DATABASE_URL"
)
if not _TEST_DATABASE_URL:
    raise RuntimeError("TEST_DATABASE_URL is required to run the backend tests.")

_DEV_DATABASE_URL = os.environ.get("DATABASE_URL") or _DOTENV.get("DATABASE_URL")
if _TEST_DATABASE_URL == _DEV_DATABASE_URL:
    raise RuntimeError(
        "TEST_DATABASE_URL must differ from DATABASE_URL; refusing to run tests "
        "against the development database."
    )

os.environ["DATABASE_URL"] = _TEST_DATABASE_URL
os.environ["APP_ENV"] = "test"
os.environ["COOKIE_SECURE"] = "false"

_MAIL_DIR = Path(tempfile.mkdtemp(prefix="odoo-prelims-mail-"))
os.environ["MAIL_DEV_DIR"] = str(_MAIL_DIR)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import delete  # noqa: E402

from app.core.security import hash_password  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.password_reset_token import PasswordResetToken  # noqa: E402
from app.models.product import Product  # noqa: E402
from app.models.refresh_token import RefreshToken  # noqa: E402
from app.models.subscription_plan import PlanFeature, SubscriptionPlan  # noqa: E402
from app.models.user import User, UserRole, UserStatus  # noqa: E402

DEFAULT_PASSWORD = "Str0ng!Pass"


@pytest.fixture(scope="session", autouse=True)
def _database_schema():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _clean_state(_database_schema):
    with SessionLocal() as db:
        db.execute(delete(PlanFeature))
        db.execute(delete(SubscriptionPlan))
        db.execute(delete(Product))
        db.execute(delete(PasswordResetToken))
        db.execute(delete(RefreshToken))
        db.execute(delete(User))
        db.commit()
    for path in _MAIL_DIR.glob("*.eml"):
        path.unlink()
    yield


@pytest.fixture
def db():
    with SessionLocal() as session:
        yield session


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def make_user(db):
    def _make_user(
        *,
        role: UserRole = UserRole.CUSTOMER,
        email: str | None = None,
        password: str = DEFAULT_PASSWORD,
        status: UserStatus = UserStatus.ACTIVE,
        full_name: str | None = None,
    ) -> User:
        user = User(
            full_name=full_name or f"{role.value.title()} User",
            email=email or f"{role.value}-{uuid4().hex[:8]}@example.com",
            hashed_password=hash_password(password),
            role=role.value,
            status=status.value,
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        db.expire_all()
        return user

    return _make_user


@pytest.fixture
def customer_user(make_user) -> User:
    return make_user(
        role=UserRole.CUSTOMER,
        email="customer@example.com",
        full_name="Customer User",
    )


@pytest.fixture
def staff_user(make_user) -> User:
    return make_user(
        role=UserRole.STAFF,
        email="staff@example.com",
        full_name="Staff User",
    )


@pytest.fixture
def admin_user(make_user) -> User:
    return make_user(
        role=UserRole.ADMIN,
        email="admin@example.com",
        full_name="Admin User",
        password="Admin!Pass123",
    )
