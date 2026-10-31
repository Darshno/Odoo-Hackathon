from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload, selectinload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.billing import Invoice
from app.models.catalog import Product, ProductVariant, SubscriptionPlan
from app.models.quotation import Quotation, QuotationLine, QuotationStatus
from app.models.subscription import Subscription, SubscriptionLine, SubscriptionStatus
from app.models.user import User, UserRole
from app.schemas.subscription import (
    PlanPurchaseRequest, PlanPurchaseResponse, SubscriptionPage, SubscriptionResponse,
)
from app.services.billing import generate_invoice
from app.services.subscriptions import add_billing_interval, process_due_subscriptions

router = APIRouter(prefix="/subscriptions", tags=["Subscriptions"])
manage_subscriptions = require_roles(UserRole.ADMIN, UserRole.STAFF)


def _load_subscription(db: Session, subscription_id: int) -> Subscription:
    subscription = db.scalar(
        select(Subscription)
        .options(joinedload(Subscription.customer), joinedload(Subscription.lines))
        .where(Subscription.id == subscription_id)
    )
    if not subscription:
        raise HTTPException(404, "Subscription not found.")
    return subscription


def _check_visibility(subscription: Subscription, user: User) -> None:
    if user.role == UserRole.CUSTOMER and subscription.customer_id != user.id:
        raise HTTPException(404, "Subscription not found.")


def _convert(
    db: Session,
    quotation_id: int,
    user: User,
    create_initial_invoice: bool = False,
) -> Subscription:
    quotation = db.scalar(
        select(Quotation)
        .options(selectinload(Quotation.lines))
        .where(Quotation.id == quotation_id)
        .with_for_update()
    )
    if not quotation:
        raise HTTPException(404, "Quotation not found.")
    if user.role == UserRole.CUSTOMER and quotation.customer_id != user.id:
        raise HTTPException(404, "Quotation not found.")
    if quotation.status != QuotationStatus.ACCEPTED:
        raise HTTPException(409, "Only accepted quotations can be converted to subscriptions.")
    if quotation.valid_until and quotation.valid_until < date.today():
        raise HTTPException(409, "Expired quotations cannot be converted to subscriptions.")
    existing = db.scalar(select(Subscription).where(Subscription.quotation_id == quotation.id).with_for_update())
    if existing:
        raise HTTPException(409, "This quotation has already been converted to a subscription.")
    if not quotation.lines or any(line.plan_id is None for line in quotation.lines):
        raise HTTPException(422, "Subscriptions require quotation lines backed by subscription plans.")
    intervals = {line.billing_interval for line in quotation.lines}
    if len(intervals) != 1 or next(iter(intervals)) not in {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}:
        raise HTTPException(422, "All subscription lines must use one supported billing interval.")
    start_date = quotation.start_date or date.today()
    interval = next(iter(intervals))
    subscription = Subscription(
        subscription_number="PENDING",
        customer_id=quotation.customer_id,
        quotation_id=quotation.id,
        status=SubscriptionStatus.ACTIVE,
        start_date=start_date,
        billing_interval=interval,
        next_billing_date=add_billing_interval(start_date, interval),
        lines=[],
    )
    for line in quotation.lines:
        plan = db.get(SubscriptionPlan, line.plan_id)
        if not plan:
            raise HTTPException(422, "A quotation plan is no longer available for subscription conversion.")
        subscription.lines.append(
            SubscriptionLine(
                plan_id=line.plan_id,
                product_id=line.product_id,
                variant_id=line.variant_id,
                product_name=line.product_name,
                variant_name=line.variant_name,
                plan_name=line.plan_name,
                sku=line.sku,
                billing_interval=line.billing_interval,
                renewal_allowed=plan.renewal_allowed,
                pause_allowed=plan.pause_allowed,
                quantity=line.quantity,
                currency=quotation.currency,
                unit_price=line.unit_price,
                tax_rate=line.tax_rate,
                tax_amount=line.tax_amount,
                amount=line.amount,
            )
        )
    db.add(subscription)
    try:
        db.flush()
        subscription.subscription_number = f"SUB-{date.today().year}-{subscription.id:06d}"
        if create_initial_invoice:
            generate_invoice(
                db, subscription.id, period_start=start_date, today=date.today(), commit=False,
            )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This quotation has already been converted to a subscription.") from exc
    except HTTPException:
        db.rollback()
        raise
    return _load_subscription(db, subscription.id)


@router.post("/from-quotation/{quotation_id}", response_model=SubscriptionResponse, status_code=status.HTTP_201_CREATED)
def create_from_quotation(
    quotation_id: int,
    create_initial_invoice: bool = False,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return _convert(db, quotation_id, user, create_initial_invoice=create_initial_invoice)


@router.post("/from-plan/{plan_id}", response_model=PlanPurchaseResponse, status_code=status.HTTP_201_CREATED)
def purchase_plan(
    plan_id: int,
    payload: PlanPurchaseRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(403, "Only customers can purchase a plan through this endpoint.")
    plan = db.scalar(
        select(SubscriptionPlan).where(SubscriptionPlan.id == plan_id).with_for_update()
    )
    if not plan or not plan.is_active:
        raise HTTPException(404, "Plan not found.")
    if payload.quantity < plan.minimum_quantity:
        raise HTTPException(422, f"This plan requires a minimum quantity of {plan.minimum_quantity}.")
    now = datetime.now(timezone.utc)
    available_from = plan.available_from
    available_until = plan.available_until
    if available_from and available_from.tzinfo is None:
        available_from = available_from.replace(tzinfo=timezone.utc)
    if available_until and available_until.tzinfo is None:
        available_until = available_until.replace(tzinfo=timezone.utc)
    if available_from and available_from > now:
        raise HTTPException(409, "This plan is not available yet.")
    if available_until and available_until < now:
        raise HTTPException(409, "This plan is no longer available.")
    product = db.get(Product, plan.product_id)
    if not product or not product.is_active:
        raise HTTPException(409, "The product for this plan is unavailable.")
    variant = db.get(ProductVariant, plan.variant_id) if plan.variant_id else None
    if plan.variant_id and (not variant or not variant.is_active or variant.product_id != product.id):
        raise HTTPException(409, "The variant for this plan is unavailable.")

    today = date.today()
    interval = plan.billing_interval.value if hasattr(plan.billing_interval, "value") else str(plan.billing_interval)
    unit_price = Decimal(plan.sales_price).quantize(Decimal("0.01"))
    subtotal = (unit_price * payload.quantity).quantize(Decimal("0.01"))
    quotation_line = QuotationLine(
        plan_id=plan.id,
        product_id=product.id,
        variant_id=variant.id if variant else None,
        product_name=product.name,
        variant_name=variant.name if variant else None,
        plan_name=plan.name,
        sku=variant.sku if variant else product.sku,
        billing_interval=interval,
        quantity=payload.quantity,
        unit_price=unit_price,
        line_total=subtotal,
        tax_rate=Decimal("0.00"),
        tax_amount=Decimal("0.00"),
        amount=subtotal,
    )
    quotation = Quotation(
        customer_id=user.id,
        created_by=user.id,
        quotation_number="PENDING",
        status=QuotationStatus.ACCEPTED,
        currency=product.currency,
        valid_until=today + timedelta(days=30),
        validity_days=30,
        start_date=today,
        subtotal=subtotal,
        tax_total=Decimal("0.00"),
        total=subtotal,
        lines=[quotation_line],
    )
    db.add(quotation)
    try:
        db.flush()
        quotation.quotation_number = f"Q-{today.year}-{quotation.id:06d}"
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "The plan purchase could not be completed.") from exc
    saved_subscription = _convert(db, quotation.id, user, create_initial_invoice=True)
    invoice = db.scalar(
        select(Invoice)
        .options(joinedload(Invoice.customer), joinedload(Invoice.lines), joinedload(Invoice.discounts))
        .where(Invoice.subscription_id == saved_subscription.id)
    )
    return {"subscription": saved_subscription, "invoice": invoice}


@router.get("", response_model=SubscriptionPage)
def list_subscriptions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    subscription_status: SubscriptionStatus | None = Query(default=None, alias="status"),
    customer_id: int | None = Query(default=None, gt=0),
    start_date_from: date | None = None,
    start_date_to: date | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = select(Subscription).join(User, Subscription.customer_id == User.id).options(
        joinedload(Subscription.customer), joinedload(Subscription.lines)
    )
    count = select(func.count(Subscription.id)).join(User, Subscription.customer_id == User.id)
    filters = []
    if user.role == UserRole.CUSTOMER:
        filters.append(Subscription.customer_id == user.id)
    elif customer_id:
        filters.append(Subscription.customer_id == customer_id)
    if subscription_status:
        filters.append(Subscription.status == subscription_status)
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Subscription.subscription_number.ilike(term), User.full_name.ilike(term), User.email.ilike(term)))
    if start_date_from:
        filters.append(Subscription.start_date >= start_date_from)
    if start_date_to:
        filters.append(Subscription.start_date <= start_date_to)
    if start_date_from and start_date_to and start_date_to < start_date_from:
        raise HTTPException(422, "start_date_to must be on or after start_date_from.")
    if filters:
        query = query.where(*filters)
        count = count.where(*filters)
    total = db.scalar(count) or 0
    items = db.scalars(
        query.order_by(Subscription.created_at.desc(), Subscription.id.desc())
        .offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return SubscriptionPage(items=items, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.get("/{subscription_id}", response_model=SubscriptionResponse)
def get_subscription(subscription_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = _load_subscription(db, subscription_id)
    _check_visibility(subscription, user)
    return subscription


def _change_status(db: Session, subscription_id: int, target: SubscriptionStatus) -> Subscription:
    subscription = _load_subscription(db, subscription_id)
    allowed = {
        SubscriptionStatus.ACTIVE: {SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED},
        SubscriptionStatus.PAUSED: {SubscriptionStatus.ACTIVE},
        SubscriptionStatus.CLOSED: {SubscriptionStatus.ACTIVE, SubscriptionStatus.PAUSED},
    }
    if subscription.status not in allowed[target]:
        raise HTTPException(409, f"Subscription cannot transition from {subscription.status.value} to {target.value}.")
    if target == SubscriptionStatus.ACTIVE and subscription.status == SubscriptionStatus.CLOSED:
        raise HTTPException(409, "Closed subscriptions cannot be reactivated.")
    subscription.status = target
    if target == SubscriptionStatus.CLOSED:
        subscription.next_billing_date = None
    db.commit()
    return _load_subscription(db, subscription.id)


def _authorize_lifecycle_action(subscription: Subscription, user: User) -> None:
    if user.role == UserRole.CUSTOMER:
        if subscription.customer_id != user.id:
            raise HTTPException(404, "Subscription not found.")
    elif user.role not in {UserRole.ADMIN, UserRole.STAFF}:
        raise HTTPException(403, "You do not have permission to manage this subscription.")


@router.post("/{subscription_id}/activate", response_model=SubscriptionResponse)
def activate_subscription(subscription_id: int, _user: User = Depends(manage_subscriptions), db: Session = Depends(get_db)):
    subscription = _load_subscription(db, subscription_id)
    if subscription.status == SubscriptionStatus.ACTIVE:
        return subscription
    if subscription.status == SubscriptionStatus.CLOSED:
        raise HTTPException(409, "Closed subscriptions cannot be reactivated.")
    return _change_status(db, subscription_id, SubscriptionStatus.ACTIVE)


@router.post("/{subscription_id}/pause", response_model=SubscriptionResponse)
def pause_subscription(subscription_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = _load_subscription(db, subscription_id)
    _authorize_lifecycle_action(subscription, user)
    if not all(line.pause_allowed for line in subscription.lines):
        raise HTTPException(409, "This subscription does not allow pausing.")
    return _change_status(db, subscription_id, SubscriptionStatus.PAUSED)

@router.post("/{subscription_id}/resume", response_model=SubscriptionResponse)
def resume_subscription(subscription_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    subscription = _load_subscription(db, subscription_id)
    _authorize_lifecycle_action(subscription, user)
    return _change_status(db, subscription_id, SubscriptionStatus.ACTIVE)


@router.post("/{subscription_id}/renew", response_model=SubscriptionResponse)
def renew_subscription(subscription_id: int, _user: User = Depends(manage_subscriptions), db: Session = Depends(get_db)):
    subscription = _load_subscription(db, subscription_id)
    if subscription.status != SubscriptionStatus.ACTIVE:
        raise HTTPException(409, "Only active subscriptions can be renewed.")
    if not all(line.renewal_allowed for line in subscription.lines):
        raise HTTPException(409, "This subscription does not allow renewal.")
    if not subscription.next_billing_date:
        subscription.next_billing_date = add_billing_interval(date.today(), subscription.billing_interval)
    else:
        subscription.last_billing_date = subscription.next_billing_date
        subscription.next_billing_date = add_billing_interval(subscription.next_billing_date, subscription.billing_interval)
    db.commit()
    return _load_subscription(db, subscription.id)


@router.post("/{subscription_id}/close", response_model=SubscriptionResponse)
def close_subscription(subscription_id: int, _user: User = Depends(manage_subscriptions), db: Session = Depends(get_db)):
    return _change_status(db, subscription_id, SubscriptionStatus.CLOSED)


@router.post("/process-due", response_model=dict)
def process_due(_user: User = Depends(manage_subscriptions), db: Session = Depends(get_db)):
    return {"processed": process_due_subscriptions(db)}
