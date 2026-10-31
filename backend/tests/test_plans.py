"""Subscription plan management API tests."""

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
):
    response = client.post(
        "/api/products",
        json={"name": name, "base_price": base_price, "product_type": "Software"},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _create_plan(
    client: TestClient,
    token: str,
    *,
    product_id: int,
    name: str = "Standard Monthly",
    billing_interval: str = "monthly",
    price: str = "1000.00",
    features: list[str] | None = None,
    status: str = "active",
):
    return client.post(
        "/api/plans",
        json={
            "product_id": product_id,
            "name": name,
            "description": "Standard plan",
            "price": price,
            "billing_interval": billing_interval,
            "features": features if features is not None else ["ERP access", "Email support"],
            "status": status,
        },
        headers=_auth(token),
    )


def test_plan_endpoints_require_authentication(client: TestClient):
    assert client.get("/api/plans").status_code == 401
    assert client.get("/api/plans/1").status_code == 401
    assert (
        client.post(
            "/api/plans",
            json={
                "product_id": 1,
                "name": "X",
                "price": 1,
                "billing_interval": "monthly",
            },
        ).status_code
        == 401
    )


def test_admin_can_create_view_edit_and_toggle_plan(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)
    product = _create_product(client, token)

    created = _create_plan(
        client,
        token,
        product_id=product["id"],
        features=["ERP access", "Email support", "ERP access", "   "],
    )
    assert created.status_code == 201, created.text
    plan = created.json()
    assert plan["name"] == "Standard Monthly"
    assert plan["billing_interval"] == "monthly"
    assert plan["status"] == "active"
    assert plan["product"]["name"] == product["name"]
    assert [feature["label"] for feature in plan["features"]] == [
        "ERP access",
        "Email support",
    ]

    listed = client.get(
        "/api/plans",
        params={"product_id": product["id"], "billing_interval": "monthly"},
        headers=_auth(token),
    )
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [plan["id"]]

    updated = client.patch(
        f"/api/plans/{plan['id']}",
        json={
            "name": "Standard Quarterly",
            "billing_interval": "quarterly",
            "price": "2700.00",
            "features": ["ERP access", "Priority support", "Quarterly review"],
        },
        headers=_auth(token),
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["name"] == "Standard Quarterly"
    assert body["billing_interval"] == "quarterly"
    assert float(body["price"]) == 2700.0
    assert [feature["label"] for feature in body["features"]] == [
        "ERP access",
        "Priority support",
        "Quarterly review",
    ]

    deactivated = client.patch(
        f"/api/plans/{plan['id']}/status",
        json={"status": "inactive"},
        headers=_auth(token),
    )
    assert deactivated.status_code == 200
    assert deactivated.json()["status"] == "inactive"

    reactivated = client.patch(
        f"/api/plans/{plan['id']}/status",
        json={"status": "active"},
        headers=_auth(token),
    )
    assert reactivated.status_code == 200
    assert reactivated.json()["status"] == "active"


def test_duplicate_plan_is_rejected(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)
    product = _create_product(client, token)
    assert _create_plan(client, token, product_id=product["id"]).status_code == 201

    duplicate = _create_plan(client, token, product_id=product["id"])
    assert duplicate.status_code == 409
    assert "already exists" in duplicate.json()["detail"]

    # Same name under a different billing interval is allowed.
    other_interval = _create_plan(
        client,
        token,
        product_id=product["id"],
        billing_interval="yearly",
    )
    assert other_interval.status_code == 201


def test_invalid_plan_data_is_rejected(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)
    product = _create_product(client, token)

    assert (
        _create_plan(
            client,
            token,
            product_id=product["id"],
            billing_interval="weekly",
        ).status_code
        == 422
    )
    assert (
        _create_plan(
            client,
            token,
            product_id=product["id"],
            price="-5.00",
        ).status_code
        == 422
    )
    assert (
        _create_plan(
            client,
            token,
            product_id=999999,
        ).status_code
        == 404
    )

    missing_product = client.post(
        "/api/plans",
        json={"name": "No Product", "price": "1.00", "billing_interval": "monthly"},
        headers=_auth(token),
    )
    assert missing_product.status_code == 422

    extra_field = client.post(
        "/api/plans",
        json={
            "product_id": product["id"],
            "name": "Sneaky",
            "price": "1.00",
            "billing_interval": "monthly",
            "status": "active",
            "role": "admin",
        },
        headers=_auth(token),
    )
    assert extra_field.status_code == 422


def test_staff_can_view_but_cannot_modify_plans(
    client: TestClient,
    admin_user: User,
    staff_user: User,
):
    admin_token = _admin_token(client, admin_user)
    product = _create_product(client, admin_token)
    created = _create_plan(client, admin_token, product_id=product["id"])
    assert created.status_code == 201
    plan_id = created.json()["id"]

    staff_token = _token(client, staff_user.email)
    assert client.get("/api/plans", headers=_auth(staff_token)).status_code == 200
    assert (
        client.get(f"/api/plans/{plan_id}", headers=_auth(staff_token)).status_code
        == 200
    )

    assert (
        _create_plan(
            client,
            staff_token,
            product_id=product["id"],
            name="Staff Plan",
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/plans/{plan_id}",
            json={"name": "Staff Rename"},
            headers=_auth(staff_token),
        ).status_code
        == 403
    )
    assert (
        client.patch(
            f"/api/plans/{plan_id}/status",
            json={"status": "inactive"},
            headers=_auth(staff_token),
        ).status_code
        == 403
    )


def test_customer_only_sees_active_plans_of_active_products(
    client: TestClient,
    admin_user: User,
    customer_user: User,
):
    admin_token = _admin_token(client, admin_user)

    active_product = _create_product(client, admin_token, name="Active Product")
    active_plan = _create_plan(
        client,
        admin_token,
        product_id=active_product["id"],
        name="Active Plan",
    )
    inactive_plan = _create_plan(
        client,
        admin_token,
        product_id=active_product["id"],
        name="Inactive Plan",
        billing_interval="yearly",
        status="inactive",
    )
    assert active_plan.status_code == 201
    assert inactive_plan.status_code == 201

    retired_product = _create_product(client, admin_token, name="Retired Product")
    retired_plan = _create_plan(
        client,
        admin_token,
        product_id=retired_product["id"],
        name="Retired Plan",
    )
    assert retired_plan.status_code == 201
    deactivated_product = client.patch(
        f"/api/products/{retired_product['id']}/status",
        json={"status": "inactive"},
        headers=_auth(admin_token),
    )
    assert deactivated_product.status_code == 200

    customer_token = _token(client, customer_user.email)
    listed = client.get(
        "/api/plans",
        params={"include_inactive": "true"},
        headers=_auth(customer_token),
    )
    assert listed.status_code == 200
    ids = {item["id"] for item in listed.json()}
    assert ids == {active_plan.json()["id"]}
    assert inactive_plan.json()["id"] not in ids
    assert retired_plan.json()["id"] not in ids

    assert (
        client.get(
            f"/api/plans/{inactive_plan.json()['id']}",
            headers=_auth(customer_token),
        ).status_code
        == 404
    )
    assert (
        client.get(
            f"/api/plans/{retired_plan.json()['id']}",
            headers=_auth(customer_token),
        ).status_code
        == 404
    )

    assert (
        _create_plan(
            client,
            customer_token,
            product_id=active_product["id"],
            name="Customer Plan",
        ).status_code
        == 403
    )


def test_plan_cannot_be_active_while_product_is_inactive(
    client: TestClient,
    admin_user: User,
):
    token = _admin_token(client, admin_user)
    product = _create_product(client, token)
    deactivated = client.patch(
        f"/api/products/{product['id']}/status",
        json={"status": "inactive"},
        headers=_auth(token),
    )
    assert deactivated.status_code == 200

    active_plan = _create_plan(client, token, product_id=product["id"])
    assert active_plan.status_code == 400
    assert "product is inactive" in active_plan.json()["detail"]

    inactive_plan = _create_plan(
        client,
        token,
        product_id=product["id"],
        status="inactive",
    )
    assert inactive_plan.status_code == 201

    cannot_activate = client.patch(
        f"/api/plans/{inactive_plan.json()['id']}/status",
        json={"status": "active"},
        headers=_auth(token),
    )
    assert cannot_activate.status_code == 400
    assert "product is inactive" in cannot_activate.json()["detail"]
