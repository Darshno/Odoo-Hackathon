from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.models.billing import Discount, DiscountType, Invoice, InvoiceDiscount, InvoiceLine, InvoiceStatus, Payment, PaymentAllocation, PaymentStatus
from app.models.subscription import Subscription, SubscriptionStatus
from app.services.subscriptions import add_billing_interval

MONEY = Decimal("0.01")


def money(value: Decimal) -> Decimal:
    return Decimal(value).quantize(MONEY, rounding=ROUND_HALF_UP)


def billing_period(start: date, interval: str) -> tuple[date, date]:
    next_start = add_billing_interval(start, interval)
    return start, next_start - timedelta(days=1)


def generate_invoice(
    db: Session,
    subscription_id: int,
    period_start: date | None = None,
    discount_id: int | None = None,
    today: date | None = None,
    issue_immediately: bool = True,
    commit: bool = True,
) -> Invoice:
    today = today or date.today()
    subscription = db.scalar(
        select(Subscription).options(joinedload(Subscription.lines)).where(Subscription.id == subscription_id).with_for_update()
    )
    if not subscription:
        raise HTTPException(404, "Subscription not found.")
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(409, "Invoices can only be generated for active subscriptions.")
    start = period_start or subscription.start_date
    if not start:
        raise HTTPException(409, "Subscription has no billing period to invoice.")
    period_start, period_end = billing_period(start, subscription.billing_interval)
    existing = db.scalar(select(Invoice).where(
        Invoice.subscription_id == subscription.id,
        Invoice.billing_period_start == period_start,
        Invoice.billing_period_end == period_end,
    ))
    if existing:
        return existing
    if subscription.end_date and period_start > subscription.end_date:
        raise HTTPException(409, "Subscription has ended.")
    subtotal = Decimal("0")
    lines = []
    for source in subscription.lines:
        line_subtotal = money(source.unit_price * source.quantity)
        subtotal += line_subtotal
        lines.append(InvoiceLine(
            subscription_line_id=source.id, plan_id=source.plan_id, product_id=source.product_id, variant_id=source.variant_id,
            product_name=source.product_name, variant_name=source.variant_name, plan_name=source.plan_name, sku=source.sku,
            billing_interval=source.billing_interval, period_start=period_start, period_end=period_end, quantity=source.quantity,
            currency=source.currency, unit_price=source.unit_price, line_subtotal=line_subtotal, discount_amount=Decimal("0"),
            tax_rate=source.tax_rate, tax_amount=Decimal("0"), line_total=Decimal("0"),
        ))
    if not lines:
        raise HTTPException(409, "Subscription has no billable lines.")
    subtotal = money(subtotal)
    discount_amount = Decimal("0")
    discount = db.scalar(select(Discount).where(Discount.id == discount_id).with_for_update()) if discount_id else None
    if discount:
        now = datetime.now(timezone.utc)
        starts_at = discount.starts_at
        expires_at = discount.expires_at
        if starts_at and starts_at.tzinfo is None:
            starts_at = starts_at.replace(tzinfo=timezone.utc)
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if not discount.is_active or (starts_at and starts_at > now) or (expires_at and expires_at < now):
            raise HTTPException(409, "Discount is not currently valid.")
        if discount.usage_limit is not None and discount.usage_count >= discount.usage_limit:
            raise HTTPException(409, "Discount usage limit has been reached.")
        if subtotal < discount.minimum_subtotal:
            raise HTTPException(409, "Invoice subtotal does not meet the discount minimum.")
        if discount.discount_type == DiscountType.PERCENTAGE:
            if discount.value > 100:
                raise HTTPException(422, "Percentage discounts cannot exceed 100.")
            discount_amount = money(subtotal * discount.value / Decimal("100"))
        else:
            if discount.currency and discount.currency != subscription.lines[0].currency:
                raise HTTPException(422, "Discount currency does not match the invoice currency.")
            discount_amount = min(money(discount.value), subtotal)
    remaining_discount = discount_amount
    tax_total = Decimal("0")
    for index, line in enumerate(lines):
        if discount_amount and subtotal:
            if index == len(lines) - 1:
                allocated_discount = remaining_discount
            else:
                allocated_discount = money(discount_amount * line.line_subtotal / subtotal)
                allocated_discount = min(allocated_discount, remaining_discount, line.line_subtotal)
            remaining_discount -= allocated_discount
        else:
            allocated_discount = Decimal("0")
        taxable_line = money(line.line_subtotal - allocated_discount)
        line.discount_amount = allocated_discount
        line.tax_amount = money(taxable_line * line.tax_rate / Decimal("100"))
        line.line_total = money(taxable_line + line.tax_amount)
        tax_total += line.tax_amount
    tax_total = money(tax_total)
    total = money(subtotal - discount_amount + tax_total)
    invoice = Invoice(
        invoice_number="PENDING", customer_id=subscription.customer_id, subscription_id=subscription.id, currency=subscription.lines[0].currency,
        status=InvoiceStatus.ISSUED if issue_immediately else InvoiceStatus.DRAFT,
        issue_date=today, due_date=today + timedelta(days=30),
        billing_period_start=period_start, billing_period_end=period_end, subtotal=subtotal, discount_total=discount_amount,
        tax_total=tax_total, total=total, amount_paid=0, amount_due=total,
        payment_terms=subscription.quotation.payment_terms, lines=lines,
    )
    if discount:
        invoice.discounts.append(InvoiceDiscount(
            discount_id=discount.id, code=discount.code, discount_type=discount.discount_type,
            value=discount.value, discount_amount=discount_amount,
        ))
    db.add(invoice)
    try:
        db.flush()
        invoice.invoice_number = f"INV-{today.year}-{invoice.id:06d}"
        if discount:
            discount.usage_count += 1
        if commit:
            db.commit()
    except IntegrityError:
        db.rollback()
        existing = db.scalar(select(Invoice).where(
            Invoice.subscription_id == subscription.id,
            Invoice.billing_period_start == period_start,
            Invoice.billing_period_end == period_end,
        ))
        if existing:
            return existing
        raise HTTPException(409, "Invoice could not be generated.")
    if not commit:
        return invoice
    return db.scalar(select(Invoice).options(joinedload(Invoice.customer), joinedload(Invoice.lines), joinedload(Invoice.discounts)).where(Invoice.id == invoice.id))


def apply_payment(db: Session, invoice_id: int, amount: Decimal, currency: str, payment_method: str, received_at: datetime | None, external_reference: str | None, notes: str | None):
    invoice = db.scalar(select(Invoice).where(Invoice.id == invoice_id).with_for_update())
    if not invoice:
        raise HTTPException(404, "Invoice not found.")
    if invoice.status == InvoiceStatus.VOID:
        raise HTTPException(409, "Void invoices cannot receive payments.")
    if invoice.status == InvoiceStatus.DRAFT:
        raise HTTPException(409, "Draft invoices cannot receive payments.")
    if currency != invoice.currency:
        raise HTTPException(422, "Payment currency does not match the invoice currency.")
    amount = money(amount)
    if amount > invoice.amount_due:
        raise HTTPException(409, "Payment exceeds the invoice outstanding balance.")
    payment = Payment(
        payment_number="PENDING", customer_id=invoice.customer_id, amount=amount, currency=currency,
        status=PaymentStatus.CONFIRMED, payment_method=payment_method, external_reference=external_reference,
        received_at=received_at or datetime.now(timezone.utc), notes=notes,
    )
    db.add(payment)
    db.flush()
    payment.payment_number = f"PAY-{payment.received_at.year}-{payment.id:06d}"
    payment.allocations.append(PaymentAllocation(invoice_id=invoice.id, amount=amount))
    invoice.amount_paid = money(invoice.amount_paid + amount)
    invoice.amount_due = money(invoice.total - invoice.amount_paid)
    if invoice.amount_due == 0:
        invoice.status = InvoiceStatus.PAID
    elif invoice.due_date < date.today():
        invoice.status = InvoiceStatus.OVERDUE
    else:
        invoice.status = InvoiceStatus.PARTIALLY_PAID
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Payment could not be recorded.") from exc
    return payment


def process_due_invoices(db: Session, today: date | None = None) -> dict[str, int]:
    today = today or date.today()
    before_count = db.scalar(select(func.count(Invoice.id))) or 0
    from app.services.subscriptions import process_due_subscriptions
    processed = process_due_subscriptions(db, today)
    overdue_count = db.query(Invoice).filter(
        Invoice.due_date < today,
        Invoice.status.in_([InvoiceStatus.ISSUED, InvoiceStatus.PARTIALLY_PAID]),
    ).update({Invoice.status: InvoiceStatus.OVERDUE}, synchronize_session=False)
    db.commit()
    after_count = db.scalar(select(func.count(Invoice.id))) or 0
    return {"invoices_created": after_count - before_count, "subscriptions_processed": processed, "invoices_marked_overdue": overdue_count}
