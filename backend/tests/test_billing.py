from datetime import date

from app.models.billing import Discount, Invoice, InvoiceStatus
from app.models.catalog import SubscriptionPlan
from app.models.subscription import Subscription, SubscriptionLine, SubscriptionStatus
from app.models.user import User, UserRole
from app.core.security import hash_password
from sqlalchemy.exc import IntegrityError


def _token(response):
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def _customer(client, email="billing@example.com"):
    return client.post("/api/auth/register", json={
        "full_name": "Billing Customer", "email": email,
        "password": "StrongPass!1", "confirm_password": "StrongPass!1",
    })


def _active_subscription(client, admin_headers, email="billing@example.com", pause=False, start_date=None):
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
        "customer_id": customer_id, "start_date": start_date,
        "lines": [{"plan_id": plan["id"], "tax_rate": "10.00"}],
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
    subscription, customer_id = _active_subscription(
        client, admin_headers, start_date="2026-10-01",
    )
    plan = db_session.get(SubscriptionPlan, subscription["lines"][0]["plan_id"])
    plan.sales_price = 999
    db_session.commit()
    response = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers)
    assert response.status_code == 201
    invoice = response.json()
    assert invoice["invoice_number"].startswith("INV-")
    assert invoice["subtotal"] == "20.00"
    assert invoice["tax_total"] == "2.00"
    assert invoice["total"] == "22.00"
    assert invoice["amount_due"] == "22.00"
    assert invoice["customer_id"] == customer_id
    assert invoice["billing_period_start"] == "2026-10-01"
    assert invoice["lines"][0]["unit_price"] == "20.00"
    assert invoice["lines"][0]["tax_rate"] == "10.00"
    assert invoice["lines"][0]["tax_amount"] == "2.00"
    assert subscription["billing_interval"] == "MONTHLY"
    assert subscription["customer_id"] == customer_id
    assert subscription["next_billing_date"] == "2026-11-01"
    assert db_session.get(Subscription, subscription["id"]).next_billing_date == date(2026, 11, 1)
    repeat = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers)
    assert repeat.status_code == 201
    assert repeat.json()["id"] == invoice["id"]
    assert db_session.query(Invoice).count() == 1


def test_partial_payment_remaining_payment_and_customer_isolation(client, admin_headers):
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
    remaining = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "12.00", "currency": "USD", "payment_method": "BANK_TRANSFER",
    })
    assert remaining.status_code == 201
    paid = client.get(f"/api/billing/invoices/{invoice['id']}", headers=admin_headers).json()
    assert paid["status"] == InvoiceStatus.PAID.value
    assert paid["amount_paid"] == "22.00"
    assert paid["amount_due"] == "0.00"
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


def test_percentage_discount_calculation(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "percentage-discount@example.com")
    discount = client.post("/api/billing/discounts", headers=admin_headers, json={
        "code": "percent10", "name": "Ten percent", "discount_type": "PERCENTAGE", "value": "10.00",
    })
    assert discount.status_code == 201
    response = client.post(
        f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers,
        json={"discount_id": discount.json()["id"]},
    )
    assert response.status_code == 201
    assert response.json()["discount_total"] == "2.00"
    assert response.json()["tax_total"] == "1.80"
    assert response.json()["total"] == "19.80"


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
    further_payment = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "0.01", "currency": "USD", "payment_method": "CASH",
    })
    assert further_payment.status_code == 409
    assert client.post(f"/api/billing/invoices/{invoice['id']}/void", headers=admin_headers).status_code == 409


def test_payment_rejects_nonpositive_amounts(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "nonpositive-payment@example.com")
    invoice = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers).json()
    for amount in ("0", "-1.00"):
        response = client.post("/api/billing/payments", headers=admin_headers, json={
            "invoice_id": invoice["id"], "amount": amount, "currency": "USD", "payment_method": "CASH",
        })
        assert response.status_code == 422


def test_overdue_partial_payment_remains_overdue_until_paid(client, admin_headers, db_session):
    subscription, _ = _active_subscription(client, admin_headers, "overdue-payment@example.com")
    invoice_data = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers).json()
    invoice = db_session.get(Invoice, invoice_data["id"])
    invoice.issue_date = date(2019, 12, 1)
    invoice.due_date = date(2020, 1, 1)
    db_session.commit()
    overdue = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert overdue.status_code == 200
    assert client.get(f"/api/billing/invoices/{invoice.id}", headers=admin_headers).json()["status"] == InvoiceStatus.OVERDUE.value
    partial = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice.id, "amount": "5.00", "currency": "USD", "payment_method": "CASH",
    })
    assert partial.status_code == 201
    still_overdue = client.get(f"/api/billing/invoices/{invoice.id}", headers=admin_headers).json()
    assert still_overdue["status"] == InvoiceStatus.OVERDUE.value
    assert still_overdue["amount_due"] == "17.00"
    final = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice.id, "amount": "17.00", "currency": "USD", "payment_method": "CASH",
    })
    assert final.status_code == 201
    assert client.get(f"/api/billing/invoices/{invoice.id}", headers=admin_headers).json()["status"] == InvoiceStatus.PAID.value


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
    rejected_payment = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "1.00", "currency": "USD", "payment_method": "CASH",
    })
    assert rejected_payment.status_code == 409


def test_due_processing_creates_invoice_and_advances_once(client, admin_headers, db_session):
    subscription_payload, _ = _active_subscription(client, admin_headers, "due-billing@example.com")
    subscription = db_session.get(Subscription, subscription_payload["id"])
    subscription.next_billing_date = date.today()
    db_session.commit()
    first = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert first.status_code == 200
    assert first.json()["invoices_created"] == 1
    assert db_session.query(Invoice).count() == 1
    invoice = db_session.query(Invoice).one()
    assert invoice.billing_period_start == date.today()
    next_date = db_session.get(Subscription, subscription.id).next_billing_date
    assert next_date > date.today()
    second = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert second.status_code == 200
    assert second.json()["invoices_created"] == 0
    assert db_session.query(Invoice).count() == 1


def test_failed_due_invoice_does_not_advance_subscription(client, admin_headers, db_session):
    subscription_payload, _ = _active_subscription(client, admin_headers, "failed-due@example.com")
    subscription = db_session.get(Subscription, subscription_payload["id"])
    subscription.next_billing_date = date.today()
    subscription.lines.clear()
    db_session.commit()
    old_next_date = subscription.next_billing_date
    response = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert response.status_code == 409
    db_session.expire_all()
    subscription = db_session.get(Subscription, subscription_payload["id"])
    assert subscription.next_billing_date == old_next_date
    assert db_session.query(Invoice).count() == 0


def test_discount_expiry_minimum_usage_and_inactive_validation(client, admin_headers, db_session):
    subscription, _ = _active_subscription(client, admin_headers, "discount-rules@example.com")
    expired = client.post("/api/billing/discounts", headers=admin_headers, json={
        "code": "expired", "name": "Expired", "discount_type": "FIXED", "value": "1.00",
        "currency": "USD", "expires_at": "2020-01-01T00:00:00Z",
    })
    assert expired.status_code == 201
    expired_active = client.post(
        f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers,
        json={"discount_id": expired.json()["id"]},
    )
    assert expired_active.status_code == 409
    inactive = client.post(f"/api/billing/discounts/{expired.json()['id']}/deactivate", headers=admin_headers)
    assert inactive.status_code == 200
    response = client.post(
        f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers,
        json={"discount_id": expired.json()["id"]},
    )
    assert response.status_code == 409
    db_discount = db_session.get(Discount, expired.json()["id"])
    assert db_discount.usage_count == 0

    limited = client.post("/api/billing/discounts", headers=admin_headers, json={
        "code": "limited", "name": "Limited", "discount_type": "PERCENTAGE", "value": "10.00",
        "minimum_subtotal": "21.00", "usage_limit": 1,
    })
    assert limited.status_code == 201
    below_minimum = client.post(
        f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers,
        json={"discount_id": limited.json()["id"]},
    )
    assert below_minimum.status_code == 409
    limited_row = db_session.get(Discount, limited.json()["id"])
    assert limited_row.usage_count == 0


def test_discount_usage_limit_is_enforced_between_invoices(client, admin_headers, db_session):
    first_subscription, _ = _active_subscription(client, admin_headers, "discount-limit-first@example.com")
    second_subscription, _ = _active_subscription(client, admin_headers, "discount-limit-second@example.com")
    discount = client.post("/api/billing/discounts", headers=admin_headers, json={
        "code": "onceonly", "name": "Once only", "discount_type": "FIXED", "value": "1.00",
        "currency": "USD", "usage_limit": 1,
    })
    assert discount.status_code == 201
    first = client.post(
        f"/api/billing/invoices/generate/{first_subscription['id']}", headers=admin_headers,
        json={"discount_id": discount.json()["id"]},
    )
    assert first.status_code == 201
    second = client.post(
        f"/api/billing/invoices/generate/{second_subscription['id']}", headers=admin_headers,
        json={"discount_id": discount.json()["id"]},
    )
    assert second.status_code == 409
    db_session.expire_all()
    assert db_session.get(Discount, discount.json()["id"]).usage_count == 1


def test_customer_cannot_generate_or_view_another_customers_billing(client, admin_headers):
    subscription, _ = _active_subscription(client, admin_headers, "billing-owner@example.com")
    invoice = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=admin_headers).json()
    stranger = _customer(client, "billing-stranger@example.com")
    stranger_headers = _token(client.post("/api/auth/login", json={
        "email": "billing-stranger@example.com", "password": "StrongPass!1",
    }))
    assert client.get(f"/api/billing/invoices/{invoice['id']}", headers=stranger_headers).status_code == 404
    payment = client.post("/api/billing/payments", headers=admin_headers, json={
        "invoice_id": invoice["id"], "amount": "1.00", "currency": "USD", "payment_method": "CASH",
    })
    assert payment.status_code == 201
    assert client.get(f"/api/billing/payments/{payment.json()['id']}", headers=stranger_headers).status_code == 404
    assert client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=stranger_headers).status_code == 403
    assert client.post("/api/billing/payments", headers=stranger_headers, json={
        "invoice_id": invoice["id"], "amount": "1.00", "currency": "USD", "payment_method": "CASH",
    }).status_code == 403
    assert client.post("/api/subscriptions/from-quotation/999", headers=stranger_headers).status_code == 404


def test_staff_can_manage_billing_and_duplicate_period_is_database_rejected(client, admin_headers, db_session):
    subscription, _ = _active_subscription(client, admin_headers, "staff-billing@example.com")
    staff = User(
        full_name="Billing Staff", email="billing-staff@example.com",
        password_hash=hash_password("StaffPass!123"), role=UserRole.STAFF,
    )
    db_session.add(staff)
    db_session.commit()
    staff_headers = _token(client.post("/api/auth/login", json={
        "email": "billing-staff@example.com", "password": "StaffPass!123",
    }))
    first = client.post(f"/api/billing/invoices/generate/{subscription['id']}", headers=staff_headers)
    assert first.status_code == 201
    original = first.json()
    duplicate = Invoice(
        invoice_number="INV-DUPLICATE",
        customer_id=original["customer_id"],
        subscription_id=original["subscription_id"],
        currency=original["currency"],
        status=InvoiceStatus.ISSUED,
        issue_date=date.fromisoformat(original["issue_date"]),
        due_date=date.fromisoformat(original["due_date"]),
        billing_period_start=date.fromisoformat(original["billing_period_start"]),
        billing_period_end=date.fromisoformat(original["billing_period_end"]),
        subtotal=original["subtotal"], discount_total=0, tax_total=original["tax_total"],
        total=original["total"], amount_paid=0, amount_due=original["total"],
    )
    db_session.add(duplicate)
    try:
        db_session.commit()
        raise AssertionError("Expected unique subscription-period constraint to reject duplicate invoice.")
    except IntegrityError:
        db_session.rollback()


def test_failed_invoice_does_not_consume_discount_usage(client, admin_headers, db_session):
    subscription_payload, _ = _active_subscription(client, admin_headers, "failed-discount-invoice@example.com")
    discount = client.post("/api/billing/discounts", headers=admin_headers, json={
        "code": "rollback1", "name": "Rollback", "discount_type": "FIXED", "value": "1.00", "currency": "USD",
    }).json()
    line = db_session.query(SubscriptionLine).filter_by(subscription_id=subscription_payload["id"]).one()
    line.quantity = 0
    db_session.commit()
    response = client.post(
        f"/api/billing/invoices/generate/{subscription_payload['id']}", headers=admin_headers,
        json={"discount_id": discount["id"]},
    )
    assert response.status_code == 409
    db_session.expire_all()
    assert db_session.get(Discount, discount["id"]).usage_count == 0


def test_due_processing_does_not_invoice_paused_or_closed_subscriptions(client, admin_headers, db_session):
    paused_payload, _ = _active_subscription(client, admin_headers, "paused-due@example.com", pause=True)
    closed_payload, _ = _active_subscription(client, admin_headers, "closed-due@example.com", pause=True)
    paused = db_session.get(Subscription, paused_payload["id"])
    closed = db_session.get(Subscription, closed_payload["id"])
    paused.status = SubscriptionStatus.PAUSED
    paused.next_billing_date = date.today()
    closed.status = SubscriptionStatus.CLOSED
    closed.next_billing_date = date.today()
    db_session.commit()
    response = client.post("/api/billing/invoices/process-due", headers=admin_headers)
    assert response.status_code == 200
    assert db_session.query(Invoice).count() == 0
    assert db_session.get(Subscription, paused.id).next_billing_date == date.today()
    assert db_session.get(Subscription, closed.id).next_billing_date == date.today()
