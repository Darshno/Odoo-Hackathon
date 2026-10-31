from datetime import date

from app.services.subscriptions import add_billing_interval
from app.models.subscription import Subscription


def _token(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _customer(client, email="subscription-customer@example.com"):
    return client.post(
        "/api/auth/register",
        json={
            "full_name": "Subscription Customer",
            "email": email,
            "password": "StrongPass!1",
            "confirm_password": "StrongPass!1",
        },
    )


def _accepted_quotation(client, admin_headers, customer_id, email, interval="MONTHLY", pause=False, renew=True):
    product = client.post(
        "/api/products", headers=admin_headers,
        json={"name": f"Product {interval}", "currency": "USD"},
    ).json()
    plan = client.post(
        "/api/plans", headers=admin_headers,
        json={
            "product_id": product["id"], "name": f"Plan {interval}", "sales_price": "20.00",
            "billing_interval": interval, "pause_allowed": pause, "renewal_allowed": renew,
        },
    ).json()
    quotation = client.post(
        "/api/quotations", headers=admin_headers,
        json={"customer_id": customer_id, "start_date": "2026-11-01", "lines": [{"plan_id": plan["id"]}]},
    ).json()
    assert client.post(f"/api/quotations/{quotation['id']}/send", headers=admin_headers).status_code == 200
    customer_headers = _customer_login(client, email)
    assert client.post(f"/api/quotations/{quotation['id']}/accept", headers=customer_headers).status_code == 200
    return quotation, customer_headers


def _customer_login(client, email):
    response = client.post(
        "/api/auth/login",
        json={"email": email, "password": "StrongPass!1"},
    )
    return _token(response)


def test_conversion_requires_accepted_quotation_and_is_one_time(client, admin_headers):
    customer = _customer(client)
    draft = client.post(
        "/api/products", headers=admin_headers, json={"name": "Draft Product", "currency": "USD"}
    ).json()
    plan = client.post(
        "/api/plans", headers=admin_headers,
        json={"product_id": draft["id"], "name": "Draft Plan", "sales_price": "10.00"},
    ).json()
    quotation = client.post(
        "/api/quotations", headers=admin_headers,
        json={"customer_id": customer.json()["user"]["id"], "lines": [{"plan_id": plan["id"]}]},
    ).json()
    assert client.post(f"/api/subscriptions/from-quotation/{quotation['id']}", headers=admin_headers).status_code == 409

    customer_headers = _token(customer)
    assert client.post(f"/api/quotations/{quotation['id']}/send", headers=admin_headers).status_code == 200
    assert client.post(f"/api/quotations/{quotation['id']}/accept", headers=customer_headers).status_code == 200
    created = client.post(f"/api/subscriptions/from-quotation/{quotation['id']}", headers=customer_headers)
    assert created.status_code == 201
    assert created.json()["subscription_number"].startswith("SUB-")
    assert created.json()["next_billing_date"] == str(add_billing_interval(date.today(), "MONTHLY"))
    assert client.post(f"/api/subscriptions/from-quotation/{quotation['id']}", headers=customer_headers).status_code == 409


def test_subscription_customer_isolation_and_admin_listing(client, admin_headers):
    first = _customer(client, "first-subscription@example.com")
    second = _customer(client, "second-subscription@example.com")
    quotation, first_headers = _accepted_quotation(
        client, admin_headers, first.json()["user"]["id"], "first-subscription@example.com"
    )
    created = client.post(f"/api/subscriptions/from-quotation/{quotation['id']}", headers=first_headers).json()
    assert client.get("/api/subscriptions", headers=first_headers).json()["total"] == 1
    assert client.get(f"/api/subscriptions/{created['id']}", headers=_token(second)).status_code == 404
    assert client.get("/api/subscriptions", headers=admin_headers).json()["total"] == 1


def test_lifecycle_enforces_pause_renewal_and_closed_state(client, admin_headers):
    customer = _customer(client, "lifecycle@example.com")
    quotation, customer_headers = _accepted_quotation(
        client, admin_headers, customer.json()["user"]["id"], email="lifecycle@example.com", pause=True, renew=True
    )
    subscription = client.post(
        f"/api/subscriptions/from-quotation/{quotation['id']}", headers=customer_headers
    ).json()
    assert client.post(f"/api/subscriptions/{subscription['id']}/pause", headers=admin_headers).status_code == 200
    assert client.post(f"/api/subscriptions/{subscription['id']}/resume", headers=admin_headers).status_code == 200
    renewed = client.post(f"/api/subscriptions/{subscription['id']}/renew", headers=admin_headers)
    assert renewed.status_code == 200
    assert renewed.json()["last_billing_date"] == "2026-12-01"
    assert client.post(f"/api/subscriptions/{subscription['id']}/close", headers=admin_headers).status_code == 200
    assert client.post(f"/api/subscriptions/{subscription['id']}/resume", headers=admin_headers).status_code == 409
    assert client.post(f"/api/subscriptions/{subscription['id']}/activate", headers=admin_headers).status_code == 409


def test_plan_renewal_rule_is_snapshotted(client, admin_headers):
    customer = _customer(client, "renewal-rule@example.com")
    quotation, customer_headers = _accepted_quotation(
        client, admin_headers, customer.json()["user"]["id"], email="renewal-rule@example.com", renew=False
    )
    subscription = client.post(
        f"/api/subscriptions/from-quotation/{quotation['id']}", headers=customer_headers
    ).json()
    assert client.post(f"/api/subscriptions/{subscription['id']}/renew", headers=admin_headers).status_code == 409


def test_billing_interval_date_calculation():
    start = date(2024, 1, 31)
    assert add_billing_interval(start, "DAILY") == date(2024, 2, 1)
    assert add_billing_interval(start, "WEEKLY") == date(2024, 2, 7)
    assert add_billing_interval(start, "MONTHLY") == date(2024, 2, 29)
    assert add_billing_interval(start, "YEARLY") == date(2025, 1, 31)


def test_due_processing_closes_nonrenewable_subscription(client, admin_headers, db_session):
    customer = _customer(client, "due-processing@example.com")
    quotation, customer_headers = _accepted_quotation(
        client, admin_headers, customer.json()["user"]["id"], email="due-processing@example.com", renew=False
    )
    subscription = client.post(
        f"/api/subscriptions/from-quotation/{quotation['id']}", headers=customer_headers
    ).json()
    row = db_session.get(Subscription, subscription["id"])
    row.next_billing_date = date.today()
    db_session.commit()
    processed = client.post("/api/subscriptions/process-due", headers=admin_headers)
    assert processed.status_code == 200
    assert processed.json()["processed"] >= 0
    detail = client.get(f"/api/subscriptions/{subscription['id']}", headers=admin_headers).json()
    assert detail["status"] == "CLOSED"
