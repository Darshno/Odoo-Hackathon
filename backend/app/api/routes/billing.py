from datetime import date, datetime, time, timedelta, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.billing import Discount, Invoice, InvoiceStatus, Payment, PaymentStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.models.user import User, UserRole
from app.schemas.billing import (
    DiscountCreate, DiscountResponse, InvoiceGenerateRequest, InvoicePage, InvoiceResponse,
    PaymentCreate, PaymentPage, PaymentResponse, RevenueAnalyticsResponse,
    SubscriptionStatusTotals,
)
from app.services.billing import apply_payment, generate_invoice, process_due_invoices

router = APIRouter(prefix="/billing", tags=["Billing"])
manage_billing = require_roles(UserRole.ADMIN, UserRole.STAFF)


def _invoice_query():
    return select(Invoice).options(
        joinedload(Invoice.customer), joinedload(Invoice.lines), joinedload(Invoice.discounts),
    )


def _load_invoice(db: Session, invoice_id: int) -> Invoice:
    invoice = db.scalar(_invoice_query().where(Invoice.id == invoice_id))
    if not invoice:
        raise HTTPException(404, "Invoice not found.")
    return invoice


def _check_invoice_visibility(invoice: Invoice, user: User) -> None:
    if user.role == UserRole.CUSTOMER and invoice.customer_id != user.id:
        raise HTTPException(404, "Invoice not found.")


@router.get("/analytics", response_model=RevenueAnalyticsResponse)
def get_revenue_analytics(
    date_from: date | None = None,
    date_to: date | None = None,
    _user: User = Depends(manage_billing),
    db: Session = Depends(get_db),
):
    end_date = date_to or date.today()
    start_date = date_from or end_date - timedelta(days=29)
    if start_date > end_date:
        raise HTTPException(422, "date_from must be on or before date_to.")

    start_at = datetime.combine(start_date, time.min, tzinfo=timezone.utc)
    end_at = datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=timezone.utc)
    paid_revenue = db.execute(
        select(Payment.currency, func.sum(Payment.amount))
        .where(
            Payment.status == PaymentStatus.CONFIRMED,
            Payment.received_at >= start_at,
            Payment.received_at < end_at,
        )
        .group_by(Payment.currency)
        .order_by(Payment.currency)
    ).all()
    outstanding_balance = db.execute(
        select(Invoice.currency, func.sum(Invoice.amount_due))
        .where(
            Invoice.status.in_((InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID, InvoiceStatus.OVERDUE)),
            Invoice.amount_due > 0,
        )
        .group_by(Invoice.currency)
        .order_by(Invoice.currency)
    ).all()
    subscription_counts = dict(db.execute(
        select(Subscription.status, func.count(Subscription.id))
        .group_by(Subscription.status)
    ).all())
    recent_payments = db.execute(
        select(Payment, User.full_name)
        .join(User, Payment.customer_id == User.id)
        .where(
            Payment.status == PaymentStatus.CONFIRMED,
            Payment.received_at >= start_at,
            Payment.received_at < end_at,
        )
        .order_by(Payment.received_at.desc(), Payment.id.desc())
        .limit(5)
    ).all()
    return {
        "date_from": start_date,
        "date_to": end_date,
        "paid_revenue": [
            {"currency": currency, "amount": amount}
            for currency, amount in paid_revenue
        ],
        "outstanding_balance": [
            {"currency": currency, "amount": amount}
            for currency, amount in outstanding_balance
        ],
        "subscriptions": SubscriptionStatusTotals(
            active=subscription_counts.get(SubscriptionStatus.ACTIVE, 0),
            paused=subscription_counts.get(SubscriptionStatus.PAUSED, 0),
            closed=subscription_counts.get(SubscriptionStatus.CLOSED, 0),
        ),
        "recent_payments": [
            {
                "id": payment.id,
                "payment_number": payment.payment_number,
                "customer_name": customer_name,
                "amount": payment.amount,
                "currency": payment.currency,
                "received_at": payment.received_at,
            }
            for payment, customer_name in recent_payments
        ],
    }


@router.get("/invoices", response_model=InvoicePage)
def list_invoices(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: str | None = None, invoice_status: InvoiceStatus | None = Query(None, alias="status"),
    customer_id: int | None = Query(None, gt=0), subscription_id: int | None = Query(None, gt=0),
    issue_date_from: date | None = None, issue_date_to: date | None = None,
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = _invoice_query().join(User, Invoice.customer_id == User.id)
    count = select(func.count(Invoice.id)).join(User, Invoice.customer_id == User.id)
    filters = []
    if user.role == UserRole.CUSTOMER:
        filters.append(Invoice.customer_id == user.id)
    elif customer_id:
        filters.append(Invoice.customer_id == customer_id)
    if subscription_id:
        filters.append(Invoice.subscription_id == subscription_id)
    if invoice_status:
        filters.append(Invoice.status == invoice_status)
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Invoice.invoice_number.ilike(term), User.full_name.ilike(term), User.email.ilike(term)))
    if issue_date_from:
        filters.append(Invoice.issue_date >= issue_date_from)
    if issue_date_to:
        filters.append(Invoice.issue_date <= issue_date_to)
    if issue_date_from and issue_date_to and issue_date_to < issue_date_from:
        raise HTTPException(422, "issue_date_to must be on or after issue_date_from.")
    if filters:
        query = query.where(*filters)
        count = count.where(*filters)
    total = db.scalar(count) or 0
    items = db.scalars(query.order_by(Invoice.created_at.desc(), Invoice.id.desc()).offset((page - 1) * page_size).limit(page_size)).unique().all()
    return InvoicePage(items=items, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.get("/invoices/{invoice_id}", response_model=InvoiceResponse)
def get_invoice(invoice_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    invoice = _load_invoice(db, invoice_id)
    _check_invoice_visibility(invoice, user)
    return invoice


@router.post("/invoices/generate/{subscription_id}", response_model=InvoiceResponse, status_code=status.HTTP_201_CREATED)
def generate_subscription_invoice(
    subscription_id: int, payload: InvoiceGenerateRequest | None = None,
    _user: User = Depends(manage_billing), db: Session = Depends(get_db),
):
    return generate_invoice(
        db, subscription_id,
        period_start=payload.period_start if payload else None,
        discount_id=payload.discount_id if payload else None,
        issue_immediately=payload.issue_immediately if payload else True,
    )


@router.post("/invoices/process-due", response_model=dict)
def process_due_invoices_route(_user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    return process_due_invoices(db)


@router.post("/invoices/{invoice_id}/void", response_model=InvoiceResponse)
def void_invoice(invoice_id: int, _user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    invoice = _load_invoice(db, invoice_id)
    if invoice.status in {InvoiceStatus.PAID, InvoiceStatus.VOID}:
        raise HTTPException(409, "Paid or already void invoices cannot be voided.")
    if invoice.amount_paid > 0:
        raise HTTPException(409, "Invoices with recorded payments cannot be voided.")
    invoice.status = InvoiceStatus.VOID
    db.commit()
    return _load_invoice(db, invoice.id)


@router.post("/invoices/{invoice_id}/issue", response_model=InvoiceResponse)
def issue_invoice(invoice_id: int, _user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    invoice = _load_invoice(db, invoice_id)
    if invoice.status == InvoiceStatus.ISSUED:
        return invoice
    if invoice.status != InvoiceStatus.DRAFT:
        raise HTTPException(409, "Only draft invoices can be issued.")
    invoice.status = InvoiceStatus.ISSUED
    db.commit()
    return _load_invoice(db, invoice.id)


@router.get("/payments", response_model=PaymentPage)
def list_payments(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    user: User = Depends(get_current_user), db: Session = Depends(get_db),
):
    query = select(Payment).options(joinedload(Payment.allocations))
    count = select(func.count(Payment.id))
    if user.role == UserRole.CUSTOMER:
        query = query.where(Payment.customer_id == user.id)
        count = count.where(Payment.customer_id == user.id)
    total = db.scalar(count) or 0
    items = db.scalars(
        query.order_by(Payment.created_at.desc(), Payment.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return PaymentPage(items=items, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.get("/payments/{payment_id}", response_model=PaymentResponse)
def get_payment(payment_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    payment = db.scalar(select(Payment).options(joinedload(Payment.allocations)).where(Payment.id == payment_id))
    if not payment or (user.role == UserRole.CUSTOMER and payment.customer_id != user.id):
        raise HTTPException(404, "Payment not found.")
    return payment


@router.post("/payments", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
def record_payment(payload: PaymentCreate, _user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    payment = apply_payment(
        db, payload.invoice_id, payload.amount, payload.currency, payload.payment_method,
        payload.received_at, payload.external_reference, payload.notes,
    )
    return db.scalar(select(Payment).options(joinedload(Payment.allocations)).where(Payment.id == payment.id))


@router.get("/discounts", response_model=list[DiscountResponse])
def list_discounts(_user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    return db.scalars(select(Discount).order_by(Discount.created_at.desc(), Discount.id.desc())).all()


@router.post("/discounts", response_model=DiscountResponse, status_code=status.HTTP_201_CREATED)
def create_discount(payload: DiscountCreate, user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    discount = Discount(**payload.model_dump(exclude={"code"}), code=payload.code.strip().upper(), created_by=user.id)
    db.add(discount)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Discount code already exists.") from exc
    db.refresh(discount)
    return discount


@router.post("/discounts/{discount_id}/deactivate", response_model=DiscountResponse)
def deactivate_discount(discount_id: int, _user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(404, "Discount not found.")
    discount.is_active = False
    db.commit()
    db.refresh(discount)
    return discount


@router.post("/discounts/{discount_id}/activate", response_model=DiscountResponse)
def activate_discount(discount_id: int, _user: User = Depends(manage_billing), db: Session = Depends(get_db)):
    discount = db.get(Discount, discount_id)
    if not discount:
        raise HTTPException(404, "Discount not found.")
    discount.is_active = True
    db.commit()
    db.refresh(discount)
    return discount
