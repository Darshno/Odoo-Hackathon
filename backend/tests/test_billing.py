from datetime import date

from app.models.billing import Invoice, InvoiceStatus
from app.models.subscription import Subscription


def _token(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _customer(client, email="billing@example.com"):
    return client.post("/api/auth/register", json={
        "full_name": "Billing Customer", "email": email,
        "password": "StrongPass!1", "confirm_password": "StrongPass!1",
    })


def _active_subscription(client, admin_headers, email="billing@example.com", pause=False):
    customer = _customer(client, email)
    customer_id = customer.json()["user"]["id"]
    product = client.post("/api/products", headers=admin_headers, json={
        "name": "Billing Product", "currency": "USD",
    }).json()
    plan = client.post("/api/plans", headers=admin_headers, json={
        "product_id": product["id"], "name": "Billing Plan", "sales_price": "20.00",
        "billing_interval": "MONTHLY", "pause_allowed": pause,
    }).json()
    quotation = client.post("/api/quotations", headers=admin_headers, json={
        "customer_id": customer_id, "lines": [{"plan_id": plan["id"], "tax_rate": "10.00"}],
    }).json()
    client.post(f"/api/quotations/{quotation['id']}/send", headers=admin_headers)
    customer_headers = _token(client.post("/api/auth/login", json={
        "email": email, "password": "StrongPass!1",
    }))
    client.post(f"/api/quotations/{quotation['id']}/accept", headers=customer_headers)
    subscription = client.post(
        f"/api/subscriptions/from-quotation/{quotation['id']}", headers=customer_headers
    ).json()
    return subscription, customer_id


def test_invoice_generation_is_historical_and_idempotent(client, admin_headers, db_session):
    subscription, customer_id = _active_subscription(client, admin_headers)
    response = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers)
    assert response.status_code == 201
    invoice = response.json()
    assert invoice["invoice_number"].startswith("INV-")
    assert invoice["subtotal"] == "20.00"
    assert invoice["tax_total"] == "2.00"
    assert invoice["total"] == "22.00"
    assert invoice["amount_due"] == "22.00"
    assert invoice["customer_id"] == customer_id
    repeat = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers)
    assert repeat.status_code == 201
    assert repeat.json()["id"] == invoice["id"]
    assert db_session.query(Invoice).count() == 1


def test_partial_payment_and_customer_isolation(client, admin_headers):
    subscription, customer_id = _active_subscription(client, admin_headers, "partial@example.com")
    invoice = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers).json()
    payment = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "10.00", "currency": "USD", "payment_method": "BANK_TRANSFER",
    })
    assert payment.status_code == 201
    detail = client.get(f"/api/billing/invoices/{invoice['id']}", headers=admin_headers).json()
    assert detail["status"] == InvoiceStatus.PARTIALLY_PAID.value
    assert detail["amount_paid"] == "10.00"
    assert detail["amount_due"] == "12.00"
    customer_headers = _token(client.post("/api/auth/login", json={
        "email": "partial@example.com", "password": "StrongPass!1",
    }))
    assert client.get(f"/api/billing/invoices/{invoice['id']}", headers=customer_headers).status_code == 200
    assert detail["customer_id"] == customer_id


def test_invoice_generation_rejects_paused_subscription(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "paused-billing@example.com", pause=True)
    assert client.post(f"/api/subscriptions/{subscription['id']}/pause", headers=admin_headers).status_code == 200
    response = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers)
    assert response.status_code == 409


def test_discount_snapshots_and_tax_are_recalculated(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "discount@example.com")
    discount_response = client.post("/api/billing/discounts", headers=admin_headers, json={
        "code": "save10", "name": "Save ten", "discount_type": "FIXED", "value": "10.00",
        "currency": "USD", "minimum_subtotal": "20.00", "usage_limit": 1,
    })
    assert discount_response.status_code == 201
    discount = discount_response.json()
    response = client.post(
        f"/api/billing/invoices/generate/{subscription['id']}",
        headers=admin_headers, json={"discount_id": discount["id"]},
    )
    assert response.status_code == 201
    invoice = response.json()
    assert invoice["discount_total"] == "10.00"
    assert invoice["tax_total"] == "1.00"
    assert invoice["total"] == "11.00"
    assert invoice["lines"][0]["discount_amount"] == "10.00"
    assert invoice["lines"][0]["tax_amount"] == "1.00"


def test_payment_cannot_overpay_and_completes_invoice(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "paid-in-full@example.com")
    invoice = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers).json()
    overpayment = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "22.01", "currency": "USD", "payment_method": "CASH",
    })
    assert overpayment.status_code == 409
    payment = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "22.00", "currency": "USD", "payment_method": "CASH",
    })
    assert payment.status_code == 201
    detail = client.get(f"/api/billing/invoices/{invoice['id']}", headers=admin_headers).json()
    assert detail["status"] == InvoiceStatus.PAID.value
    assert detail["amount_due"] == "0.00"


def test_draft_invoice_requires_issue_and_unpaid_invoice_can_be_voided(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "draft-invoice@example.com")
    response = client.post(
        f"/api/billing/invoices/generate/{subscription['id']}",
        headers=admin_headers, json={"issue_immediately": False},
    )
    assert response.status_code == 201
    invoice = response.json()
    assert invoice["status"] == InvoiceStatus.DRAFT.value
    issued = client.post(f"/api/billing/invoices/{invoice['id']}/issue", headers=admin_headers)
    assert issued.status_code == 200
    assert issued.json()["status"] == InvoiceStatus.ISSUED.value
    voided = client.post(f"/api/billing/invoices/{invoice['id']}/void", headers=admin_headers)
    assert voided.status_code == 200
    assert voided.json()["status"] == InvoiceStatus.VOID.value


def test_due_processing_creates_invoice_and_advances_once(client, admin_headers, db_session):
    subscription_payload, _ = _active_subscription(client, admin_headers, "due-billing@example.com")
    subscription = db_session.get(Subscription, subscription_payload["id"])
    subscription.next_billing_date = date.today()
    db_session.commit()
    first = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert first.status_code == 200
    assert first.json()["invoices_created"] == 1
    assert db_session.query(Invoice).count() == 1
    second = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["invoices_created"] == 0
    assert db_session.query(Invoice).count() == 1
