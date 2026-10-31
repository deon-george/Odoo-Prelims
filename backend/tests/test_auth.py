"""Authentication tests: registration, login, sessions, password reset."""

from __future__ import annotations

import re
from email import message_from_bytes

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.routes.auth import REFRESH_COOKIE_NAME
from app.core.config import settings
from app.core.security import hash_opaque_token
from app.models.refresh_token import RefreshToken
from app.models.user import User

DEFAULT_PASSWORD = "Str0ng!Pass"


def _login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _latest_reset_token() -> str:
    files = sorted(settings.mail_dev_path.glob("*.eml"))
    assert files, "expected a password reset email in the dev outbox"
    message = message_from_bytes(files[-1].read_bytes())
    body = message.get_payload(decode=True).decode("utf-8")
    match = re.search(r"token=([A-Za-z0-9_\-]+)", body)
    assert match, "reset link token not found in email body"
    return match.group(1)


def test_register_customer_success(client: TestClient, db):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "New Customer",
            "email": "New.Customer@Example.com",
            "password": DEFAULT_PASSWORD,
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["role"] == "customer"
    assert body["status"] == "active"
    assert body["email"] == "new.customer@example.com"
    assert "password" not in body
    assert "hashed_password" not in body

    db.rollback()
    user = db.scalar(select(User).where(User.email == "new.customer@example.com"))
    assert user is not None
    assert user.role == "customer"
    assert user.hashed_password != DEFAULT_PASSWORD
    assert user.hashed_password.startswith("$argon2id$")


def test_register_duplicate_email_case_insensitive(client: TestClient):
    payload = {
        "full_name": "Duplicate User",
        "email": "duplicate@example.com",
        "password": DEFAULT_PASSWORD,
    }
    assert client.post("/api/auth/register", json=payload).status_code == 201

    payload["email"] = "DUPLICATE@example.com"
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 409
    assert "already exists" in response.json()["detail"].lower()


def test_register_rejects_weak_passwords(client: TestClient):
    cases = [
        "Short!1",  # too short
        "alllowercase!",  # no uppercase
        "ALLUPPERCASE!",  # no lowercase
        "NoSpecial123",  # no special character
    ]
    for index, password in enumerate(cases):
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Weak Password",
                "email": f"weak-{index}@example.com",
                "password": password,
            },
        )
        assert response.status_code == 422, password


def test_register_cannot_inject_role(client: TestClient):
    response = client.post(
        "/api/auth/register",
        json={
            "full_name": "Role Injector",
            "email": "injector@example.com",
            "password": DEFAULT_PASSWORD,
            "role": "admin",
        },
    )
    assert response.status_code == 422


def test_register_cannot_set_staff_or_admin_fields(client: TestClient):
    for field in ("status", "hashed_password"):
        response = client.post(
            "/api/auth/register",
            json={
                "full_name": "Field Injector",
                "email": f"inject-{field}@example.com",
                "password": DEFAULT_PASSWORD,
                field: "active" if field == "status" else "$argon2id$fake",
            },
        )
        assert response.status_code == 422


def test_login_success_and_current_user(client: TestClient, customer_user: User):
    response = _login(client, customer_user.email)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] > 0
    assert body["user"]["email"] == customer_user.email
    assert body["user"]["role"] == "customer"
    assert client.cookies.get(REFRESH_COOKIE_NAME)

    me = client.get("/api/auth/me", headers=_auth(body["access_token"]))
    assert me.status_code == 200
    assert me.json()["id"] == customer_user.id


def test_login_rejects_wrong_password(client: TestClient, customer_user: User):
    response = _login(client, customer_user.email, "Wrong!Pass123")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."
    assert client.cookies.get(REFRESH_COOKIE_NAME) is None


def test_login_rejects_unknown_email(client: TestClient):
    response = _login(client, "nobody@example.com")
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."


def test_login_rejects_inactive_account(client: TestClient, make_user):
    from app.models.user import UserRole, UserStatus

    user = make_user(
        role=UserRole.CUSTOMER,
        email="inactive@example.com",
        status=UserStatus.INACTIVE,
    )
    response = _login(client, user.email)
    assert response.status_code == 403


def test_current_user_requires_valid_token(client: TestClient, customer_user: User):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers=_auth("not-a-token")).status_code == 401

    token = _login(client, customer_user.email).json()["access_token"]
    assert client.get("/api/auth/me", headers=_auth(token + "x")).status_code == 401


def test_refresh_rotates_cookie_and_logout_revokes(
    client: TestClient,
    customer_user: User,
    db,
):
    assert _login(client, customer_user.email).status_code == 200
    old_refresh = client.cookies.get(REFRESH_COOKIE_NAME)
    assert old_refresh

    refreshed = client.post("/api/auth/refresh")
    assert refreshed.status_code == 200, refreshed.text
    new_refresh = client.cookies.get(REFRESH_COOKIE_NAME)
    assert new_refresh and new_refresh != old_refresh

    # End this session's transaction so the HTTP client's committed writes are
    # visible (MySQL REPEATABLE READ keeps an old snapshot otherwise).
    db.rollback()
    old_record = db.scalar(
        select(RefreshToken).where(
            RefreshToken.token_hash == hash_opaque_token(old_refresh)
        )
    )
    assert old_record is not None
    assert old_record.revoked_at is not None

    assert client.post("/api/auth/logout").status_code == 200
    assert client.post("/api/auth/refresh").status_code == 401


def test_password_reset_flow(client: TestClient, customer_user: User):
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": customer_user.email},
    )
    assert response.status_code == 202
    assert "if an account exists" in response.json()["message"].lower()

    token = _latest_reset_token()
    new_password = "BrandNew!Pass9"

    reset = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": new_password},
    )
    assert reset.status_code == 200, reset.text

    assert _login(client, customer_user.email, DEFAULT_PASSWORD).status_code == 401
    assert _login(client, customer_user.email, new_password).status_code == 200

    reuse = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "Another!Pass9"},
    )
    assert reuse.status_code == 400


def test_forgot_password_unknown_email_is_generic(client: TestClient):
    response = client.post(
        "/api/auth/forgot-password",
        json={"email": "missing@example.com"},
    )
    assert response.status_code == 202
    assert "if an account exists" in response.json()["message"].lower()
    assert not list(settings.mail_dev_path.glob("*.eml"))


def test_reset_rejects_weak_new_password(client: TestClient, customer_user: User):
    client.post("/api/auth/forgot-password", json={"email": customer_user.email})
    token = _latest_reset_token()
    response = client.post(
        "/api/auth/reset-password",
        json={"token": token, "new_password": "weak"},
    )
    assert response.status_code == 422
