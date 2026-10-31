"""Product management API tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.models.user import User

DEFAULT_PASSWORD = "Str0ng!Pass"
ADMIN_PASSWORD = "Admin!Pass123"


def _token(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> str:
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _admin_token(client: TestClient, admin_user: User) -> str:
    return _token(client, admin_user.email, ADMIN_PASSWORD)


def _create_product(
    client: TestClient,
    token: str,
    *,
    name: str = "Odoo ERP",
    base_price: str = "1000.00",
    status: str = "active",
    description: str | None = "Full ERP suite",
    product_type: str | None = "Software",
):
    return client.post(
        "/api/products",
        json={
            "name": name,
            "description": description,
            "product_type": product_type,
            "base_price": base_price,
            "status": status,
        },
        headers=_auth(token),
    )


def test_product_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/products").status_code == 401
    assert client.get("/api/products/1").status_code == 401
    assert client.post("/api/products", json={"name": "X", "base_price": 1}).status_code == 401


def test_admin_can_create_view_edit_and_toggle_product(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)

    created = _create_product(client, token)
    assert created.status_code == 201, created.text
    product = created.json()
    assert product["name"] == "Odoo ERP"
    assert product["description"] == "Full ERP suite"
    assert product["product_type"] == "Software"
    assert product["status"] == "active"
    assert float(product["base_price"]) == 1000.0

    listed = client.get("/api/products", headers=_auth(token))
    assert listed.status_code == 200
    assert any(item["id"] == product["id"] for item in listed.json())

    updated = client.patch(
        f"/api/products/{product['id']}",
        json={"name": "Odoo ERP Standard", "base_price": "1250.50"},
        headers=_auth(token),
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["name"] == "Odoo ERP Standard"
    assert float(updated.json()["base_price"]) == 1250.50

    deactivated = client.patch(
        f"/api/products/{product['id']}/status",
        json={"status": "inactive"},
        headers=_auth(token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"

    reactivated = client.patch(
        f"/api/products/{product['id']}/status",
        json={"status": "active"},
        headers=_auth(token),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_duplicate_product_name_is_rejected(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)
    assert _create_product(client, token).status_code == 201

    duplicate = _create_product(client, token)
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]


def test_invalid_product_data_is_rejected(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)

    negative_price = _create_product(client, token, base_price="-1.00")
    assert negative_price.status_code == 422

    blank_name = _create_product(client, token, name="   ")
    assert blank_name.status_code == 422

    invalid_status = _create_product(client, token, status="archived")
    assert invalid_status.status_code == 422

    extra_field = client.post(
        "/api/products",
        json={"name": "Sneaky", "base_price": "1.00", "role": "admin"},
        headers=_auth(token),
    )
    assert extra_field.status_code == 422

    assert client.patch(
        "/api/products/999999",
        json={"name": "Missing"},
        headers=_auth(token),
    ).status_code == 404


def test_staff_can_view_but_cannot_modify_products(
    client: TestClient,
    admin_user: User,
    staff_user: User,
):
    admin_token = _admin_token(client, admin_user)
    created = _create_product(client, admin_token)
    assert created.status_code == 201
    product_id = created.json()["id"]

    staff_token = _token(client, staff_user.email)
    assert client.get("/api/products", headers=_auth(staff_token)).status_code == 200
    assert (
        client.get(f"/api/products/{product_id}", headers=_auth(staff_token)).status_code
        == 200
    )

    assert (
        _create_product(client, staff_token, name="Staff Product").status_code == 403
    )
    assert (
        client.patch(
            f"/api/products/{product_id}",
            json={"name": "Staff Rename"},
            headers=_auth(staff_token),
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/products/{product_id}/status",
            json={"status": "inactive"},
            headers=_auth(staff_token),
        ).status_code
        == 403
    )


def test_customer_only_sees_active_products(
    client: TestClient,
    admin_user: User,
    customer_user: User,
):
    admin_token = _admin_token(client, admin_user)
    active = _create_product(client, admin_token, name="Active Product")
    inactive = _create_product(
        client,
        admin_token,
        name="Retired Product",
        status="inactive",
    )
    assert active.status_code == 201
    assert inactive.status_code == 201
    active_id = active.json()["id"]
    inactive_id = inactive.json()["id"]

    customer_token = _token(client, customer_user.email)
    listed = client.get(
        "/api/products",
        params={"include_inactive": "true"},
        headers=_auth(customer_token),
    )
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert active_id in ids
    assert inactive_id not in ids

    assert (
        client.get(
            f"/api/products/{active_id}",
            headers=_auth(customer_token),
        ).status_code
        == 200
    )
    assert (
        client.get(
            f"/api/products/{inactive_id}",
            headers=_auth(customer_token),
        ).status_code
        == 404
    )

    assert (
        _create_product(client, customer_token, name="Customer Product").status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/products/{active_id}",
            json={"name": "Customer Rename"},
            headers=_auth(customer_token),
        ).status_code
        == 403
    )
