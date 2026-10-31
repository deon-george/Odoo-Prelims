"""Role-based access control tests for admin/staff/customer boundaries."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User

DEFAULT_PASSWORD = "Str0ng!Pass"


def _login(client: TestClient, email: str, password: str = DEFAULT_PASSWORD):
    return client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )


def _token(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    response = _login(client, email, password)
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


STAFF_PAYLOAD = {
    "full_name": "New Staff",
    "email": "new.staff@example.com",
    "password": "Staff!Pass123",
}


def test_admin_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/admin/users").status_code == 401
    assert client.post("/api/admin/staff", json=STAFF_PAYLOAD).status_code == 401
    assert (
        client.patch("/api/admin/users/1/status", json={"status": "inactive"}).status_code
        == 401
    )


def test_customer_cannot_access_admin_endpoints(
    client: TestClient,
    customer_user: User,
):
    token = _token(client, customer_user.email)
    assert client.get("/api/admin/users", headers=_auth(token)).status_code == 403
    assert (
        client.post(
            "/api/admin/staff",
            json=STAFF_PAYLOAD,
            headers=_auth(token),
        ).status_code
        == 403
    )


def test_staff_cannot_create_staff_or_admin_and_cannot_list_users(
    client: TestClient,
    staff_user: User,
):
    token = _token(client, staff_user.email)
    assert (
        client.post(
            "/api/admin/staff",
            json=STAFF_PAYLOAD,
            headers=_auth(token),
        ).status_code
        == 403
    )
    assert client.get("/api/admin/users", headers=_auth(token)).status_code == 403


def test_staff_cannot_promote_self_by_injecting_role(
    client: TestClient,
    staff_user: User,
):
    token = _token(client, staff_user.email)
    response = client.post(
        "/api/admin/staff",
        json={
            "full_name": "Escalation Attempt",
            "email": "escalation@example.com",
            "password": "Escalate!123",
            "role": "admin",
        },
        headers=_auth(token),
    )
    assert response.status_code == 403


def test_admin_can_create_staff_and_list_users(
    client: TestClient,
    admin_user: User,
    db,
):
    token = _token(client, admin_user.email, "Admin!Pass123")

    created = client.post(
        "/api/admin/staff",
        json=STAFF_PAYLOAD,
        headers=_auth(token),
    )
    assert created.status_code == 201, created.text
    body = created.json()
    assert body["role"] == "staff"
    assert body["status"] == "active"
    assert body["email"] == STAFF_PAYLOAD["email"]

    listed = client.get("/api/admin/users", headers=_auth(token))
    assert listed.status_code == 200
    emails = {user["email"] for user in listed.json()}
    assert {admin_user.email, STAFF_PAYLOAD["email"]}.issubset(emails)


def test_admin_can_deactivate_and_reactivate_staff(
    client: TestClient,
    admin_user: User,
    staff_user: User,
):
    admin_token = _token(client, admin_user.email, "Admin!Pass123")

    deactivated = client.patch(
        f"/api/admin/users/{staff_user.id}/status",
        json={"status": "inactive"},
        headers=_auth(admin_token),
    )
    assert deactivated.status_code == 200, deactivated.text
    assert deactivated.json()["status"] == "inactive"
    assert _login(client, staff_user.email).status_code == 403

    reactivated = client.patch(
        f"/api/admin/users/{staff_user.id}/status",
        json={"status": "active"},
        headers=_auth(admin_token),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"
    assert _login(client, staff_user.email).status_code == 200


def test_admin_cannot_change_another_admin_status(
    client: TestClient,
    admin_user: User,
    make_user,
):
    from app.models.user import UserRole

    second_admin = make_user(
        role=UserRole.ADMIN,
        email="second.admin@example.com",
        password="Admin!Pass456",
    )
    admin_token = _token(client, admin_user.email, "Admin!Pass123")

    response = client.patch(
        f"/api/admin/users/{second_admin.id}/status",
        json={"status": "inactive"},
        headers=_auth(admin_token),
    )
    assert response.status_code == 403


def test_admin_can_create_only_staff_role(client: TestClient, admin_user: User):
    token = _token(client, admin_user.email, "Admin!Pass123")
    response = client.post(
        "/api/admin/staff",
        json={
            "full_name": "Sneaky Admin",
            "email": "sneaky.admin@example.com",
            "password": "Sneaky!Pass123",
            "role": "admin",
        },
        headers=_auth(token),
    )
    assert response.status_code == 422
