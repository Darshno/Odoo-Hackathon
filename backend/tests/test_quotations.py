from sqlalchemy import select

from app.models.quotation import Quotation


def _token(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _customer(client, email="customer@example.com"):
    return client.post(
        "/api/auth/register",
        json={
            "full_name": "Quotation Customer",
            "email": email,
            "password": "StrongPass!1",
            "confirm_password": "StrongPass!1",
        },
    )


def _catalog(client, headers, price="12.50"):
    product = client.post(
        "/api/products",
        headers=headers,
        json={"name": "Workspace", "sku": "WORKSPACE", "currency": "USD"},
    ).json()
    plan = client.post(
        "/api/plans",
        headers=headers,
        json={
            "product_id": product["id"],
            "name": "Monthly Pro",
            "sales_price": price,
            "billing_interval": "MONTHLY",
        },
    )
    return plan.json()


def test_admin_creates_quotation_with_totals_and_snapshots(client, admin_headers, db_session):
    customer = _customer(client)
    customer_id = customer.json()["user"]["id"]
    plan = _catalog(client, admin_headers)

    response = client.post(
        "/api/quotations",
        headers=admin_headers,
        json={"customer_id": customer_id, "lines": [{"plan_id": plan["id"], "quantity": 3}]},
    )

    assert response.status_code == 201
    body = response.json()
    assert body["quotation_number"].startswith("Q-")
    assert body["status"] == "DRAFT"
    assert body["subtotal"] == "37.50"
    assert body["total"] == "37.50"
    assert body["lines"][0]["product_name"] == "Workspace"
    assert body["lines"][0]["unit_price"] == "12.50"
    assert db_session.scalar(select(Quotation).where(Quotation.id == body["id"])).quotation_number == body["quotation_number"]


def test_quotation_number_is_unique_and_catalog_changes_do_not_change_snapshot(client, admin_headers):
    customer = _customer(client)
    plan = _catalog(client, admin_headers, "10.00")
    first = client.post(
        "/api/quotations",
        headers=admin_headers,
        json={"customer_id": customer.json()["user"]["id"], "lines": [{"plan_id": plan["id"]}]},
    )
    assert first.status_code == 201
    client.patch(f"/api/plans/{plan['id']}", headers=admin_headers, json={"sales_price": "99.00", "name": "Changed"})
    detail = client.get(f"/api/quotations/{first.json()['id']}", headers=admin_headers)
    assert detail.json()["lines"][0]["plan_name"] == "Monthly Pro"
    assert detail.json()["lines"][0]["unit_price"] == "10.00"


def test_quotation_visibility_and_transitions(client, admin_headers):
    customer = _customer(client)
    customer_headers = _token(customer)
    plan = _catalog(client, admin_headers)
    quotation = client.post(
        "/api/quotations",
        headers=admin_headers,
        json={"customer_id": customer.json()["user"]["id"], "lines": [{"plan_id": plan["id"]}]},
    ).json()

    assert client.get("/api/quotations", headers=customer_headers).json()["total"] == 1
    assert client.post(f"/api/quotations/{quotation['id']}/send", headers=admin_headers).status_code == 200
    accepted = client.post(f"/api/quotations/{quotation['id']}/accept", headers=customer_headers)
    assert accepted.status_code == 200
    assert accepted.json()["status"] == "ACCEPTED"
    assert client.post(f"/api/quotations/{quotation['id']}/accept", headers=customer_headers).status_code == 409


def test_customer_cannot_create_or_see_other_customer_quotation(client, admin_headers):
    first = _customer(client, "one@example.com")
    second = _customer(client, "two@example.com")
    plan = _catalog(client, admin_headers)
    quotation = client.post(
        "/api/quotations",
        headers=admin_headers,
        json={"customer_id": first.json()["user"]["id"], "lines": [{"plan_id": plan["id"]}]},
    ).json()

    assert client.post(
        "/api/quotations",
        headers=_token(second),
        json={"customer_id": second.json()["user"]["id"], "lines": [{"plan_id": plan["id"]}]},
    ).status_code == 403
    assert client.get(f"/api/quotations/{quotation['id']}", headers=_token(second)).status_code == 404


def test_quotation_list_supports_status_and_pagination(client, admin_headers):
    customer = _customer(client)
    plan = _catalog(client, admin_headers)
    for _ in range(2):
        assert client.post(
            "/api/quotations",
            headers=admin_headers,
            json={"customer_id": customer.json()["user"]["id"], "lines": [{"plan_id": plan["id"]}]},
        ).status_code == 201

    response = client.get("/api/quotations?page=1&page_size=1&status=DRAFT", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert len(response.json()["items"]) == 1


def test_template_creation_listing_and_quotation_creation(client, admin_headers):
    customer = _customer(client)
    plan = _catalog(client, admin_headers, "15.25")
    template = client.post(
        "/api/quotations/templates",
        headers=admin_headers,
        json={
            "name": "Standard Pro",
            "description": "Default monthly package",
            "validity_days": 14,
            "lines": [{"plan_id": plan["id"], "quantity": 2}],
        },
    )
    assert template.status_code == 201
    assert template.json()["validity_days"] == 14
    assert client.get("/api/quotations/templates", headers=admin_headers).json()["total"] == 1

    quotation = client.post(
        "/api/quotations/from-template",
        headers=admin_headers,
        json={"template_id": template.json()["id"], "customer_id": customer.json()["user"]["id"]},
    )
    assert quotation.status_code == 201
    assert quotation.json()["subtotal"] == "30.50"
    assert quotation.json()["validity_days"] == 14
    assert quotation.json()["template_id"] == template.json()["id"]


def test_inactive_template_and_invalid_line_are_rejected(client, admin_headers):
    customer = _customer(client, "template-customer@example.com")
    invalid = client.post(
        "/api/quotations/templates",
        headers=admin_headers,
        json={"name": "Invalid", "lines": [{"plan_id": 99999}]},
    )
    assert invalid.status_code == 422
    plan = _catalog(client, admin_headers)
    template = client.post(
        "/api/quotations/templates",
        headers=admin_headers,
        json={"name": "Inactive", "lines": [{"plan_id": plan["id"]}]},
    ).json()
    assert client.patch(
        f"/api/quotations/templates/{template['id']}/status?is_active=false", headers=admin_headers
    ).status_code == 200
    response = client.post(
        "/api/quotations/from-template",
        headers=admin_headers,
        json={"template_id": template["id"], "customer_id": customer.json()["user"]["id"]},
    )
    assert response.status_code == 422


def test_product_only_template_line_can_create_quotation(client, admin_headers):
    customer = _customer(client, "product-template@example.com")
    product = client.post(
        "/api/products",
        headers=admin_headers,
        json={"name": "Implementation", "sales_price": "20.00", "currency": "USD"},
    ).json()
    template = client.post(
        "/api/quotations/templates",
        headers=admin_headers,
        json={"name": "Product Only", "lines": [{"product_id": product["id"], "quantity": 2}]},
    ).json()
    response = client.post(
        "/api/quotations/from-template",
        headers=admin_headers,
        json={"template_id": template["id"], "customer_id": customer.json()["user"]["id"]},
    )
    assert response.status_code == 201
    assert response.json()["subtotal"] == "40.00"
