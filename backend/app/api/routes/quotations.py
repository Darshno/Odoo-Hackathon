from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.catalog import SubscriptionPlan
from app.models.quotation import Quotation, QuotationLine, QuotationStatus
from app.models.user import User, UserRole
from app.schemas.quotation import QuotationCreate, QuotationPage, QuotationResponse, QuotationUpdate

router = APIRouter(prefix="/quotations", tags=["Quotations"])
manage_quotations = require_roles(UserRole.ADMIN, UserRole.STAFF)
MONEY = Decimal("0.01")


def _money(value: Decimal) -> Decimal:
    return value.quantize(MONEY, rounding=ROUND_HALF_UP)


def _load_quotation(db: Session, quotation_id: int) -> Quotation:
    quotation = db.scalar(
        select(Quotation)
        .options(joinedload(Quotation.customer), joinedload(Quotation.lines))
        .where(Quotation.id == quotation_id)
    )
    if not quotation:
        raise HTTPException(404, "Quotation not found.")
    return quotation


def _ensure_customer(db: Session, customer_id: int) -> User:
    customer = db.get(User, customer_id)
    if not customer or customer.role != UserRole.CUSTOMER or not customer.is_active:
        raise HTTPException(422, "Quotation customer must be an active CUSTOMER account.")
    return customer


def _build_lines(db: Session, payload_lines) -> tuple[list[QuotationLine], str, Decimal]:
    lines: list[QuotationLine] = []
    currency: str | None = None
    subtotal = Decimal("0")
    for payload in payload_lines:
        plan = db.scalar(
            select(SubscriptionPlan)
            .options(joinedload(SubscriptionPlan.product), joinedload(SubscriptionPlan.variant))
            .where(SubscriptionPlan.id == payload.plan_id)
        )
        if not plan or not plan.is_active:
            raise HTTPException(422, "Every quotation plan must be active.")
        if plan.available_from and plan.available_from > datetime.now(timezone.utc):
            raise HTTPException(422, "Every quotation plan must currently be available.")
        if plan.available_until and plan.available_until < datetime.now(timezone.utc):
            raise HTTPException(422, "Every quotation plan must currently be available.")
        product = plan.product
        if not product or not product.is_active:
            raise HTTPException(422, "Every quotation product must be active.")
        if plan.variant_id and (not plan.variant or not plan.variant.is_active):
            raise HTTPException(422, "Every quotation variant must be active.")
        if currency is None:
            currency = product.currency
        elif currency != product.currency:
            raise HTTPException(422, "All quotation lines must use the same currency.")
        unit_price = _money(Decimal(plan.sales_price))
        line_total = _money(unit_price * payload.quantity)
        subtotal += line_total
        lines.append(
            QuotationLine(
                plan_id=plan.id,
                product_id=product.id,
                variant_id=plan.variant_id,
                product_name=product.name,
                variant_name=plan.variant.name if plan.variant else None,
                plan_name=plan.name,
                sku=plan.variant.sku if plan.variant else product.sku,
                billing_interval=plan.billing_interval.value if hasattr(plan.billing_interval, "value") else str(plan.billing_interval),
                quantity=payload.quantity,
                unit_price=unit_price,
                line_total=line_total,
            )
        )
    return lines, currency or "USD", _money(subtotal)


def _commit(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Quotation could not be saved because of a conflicting record.") from exc


def _check_visibility(quotation: Quotation, user: User) -> None:
    if user.role == UserRole.CUSTOMER and quotation.customer_id != user.id:
        raise HTTPException(404, "Quotation not found.")


def _transition(db: Session, quotation_id: int, user: User, target: QuotationStatus) -> Quotation:
    quotation = _load_quotation(db, quotation_id)
    _check_visibility(quotation, user)
    allowed = {
        QuotationStatus.SENT: {QuotationStatus.DRAFT},
        QuotationStatus.ACCEPTED: {QuotationStatus.SENT},
        QuotationStatus.REJECTED: {QuotationStatus.SENT},
        QuotationStatus.CANCELLED: {QuotationStatus.DRAFT, QuotationStatus.SENT},
    }
    if target in {QuotationStatus.ACCEPTED, QuotationStatus.REJECTED} and user.role != UserRole.CUSTOMER:
        pass
    elif target == QuotationStatus.SENT and user.role not in {UserRole.ADMIN, UserRole.STAFF}:
        raise HTTPException(403, "You do not have permission to send quotations.")
    elif target == QuotationStatus.CANCELLED and user.role not in {UserRole.ADMIN, UserRole.STAFF}:
        raise HTTPException(403, "You do not have permission to cancel quotations.")
    if quotation.status not in allowed[target]:
        raise HTTPException(409, f"Quotation cannot transition from {quotation.status.value} to {target.value}.")
    if target in {QuotationStatus.ACCEPTED, QuotationStatus.REJECTED} and quotation.valid_until and quotation.valid_until < date.today():
        raise HTTPException(409, "Expired quotations cannot be accepted or rejected.")
    quotation.status = target
    _commit(db)
    return _load_quotation(db, quotation.id)


@router.post("", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def create_quotation(payload: QuotationCreate, user: User = Depends(manage_quotations), db: Session = Depends(get_db)):
    customer = _ensure_customer(db, payload.customer_id)
    lines, currency, subtotal = _build_lines(db, payload.lines)
    quotation = Quotation(
        customer_id=customer.id,
        created_by=user.id,
        quotation_number="PENDING",
        currency=currency,
        valid_until=payload.valid_until,
        notes=payload.notes,
        subtotal=subtotal,
        total=subtotal,
        lines=lines,
    )
    db.add(quotation)
    db.flush()
    quotation.quotation_number = f"Q-{datetime.now(timezone.utc).year}-{quotation.id:06d}"
    _commit(db)
    return _load_quotation(db, quotation.id)


@router.get("", response_model=QuotationPage)
def list_quotations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    quotation_status: QuotationStatus | None = Query(default=None, alias="status"),
    customer_id: int | None = Query(default=None, gt=0),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    filters = []
    if user.role == UserRole.CUSTOMER:
        filters.append(Quotation.customer_id == user.id)
    elif customer_id is not None:
        filters.append(Quotation.customer_id == customer_id)
    if quotation_status:
        filters.append(Quotation.status == quotation_status)
    query = select(Quotation).options(joinedload(Quotation.customer), joinedload(Quotation.lines))
    count = select(func.count(Quotation.id))
    if filters:
        query = query.where(*filters)
        count = count.where(*filters)
    total = db.scalar(count) or 0
    quotations = db.scalars(
        query.order_by(Quotation.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return QuotationPage(items=quotations, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.get("/{quotation_id}", response_model=QuotationResponse)
def get_quotation(quotation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    quotation = _load_quotation(db, quotation_id)
    _check_visibility(quotation, user)
    return quotation


@router.patch("/{quotation_id}", response_model=QuotationResponse)
def update_quotation(
    quotation_id: int, payload: QuotationUpdate, _user: User = Depends(manage_quotations), db: Session = Depends(get_db)
):
    quotation = _load_quotation(db, quotation_id)
    if quotation.status != QuotationStatus.DRAFT:
        raise HTTPException(409, "Only draft quotations can be edited.")
    if payload.lines is not None:
        lines, currency, subtotal = _build_lines(db, payload.lines)
        if currency != quotation.currency:
            raise HTTPException(422, "Updated quotation lines must use the existing quotation currency.")
        quotation.lines = lines
        quotation.subtotal = subtotal
        quotation.total = subtotal
    if "valid_until" in payload.model_fields_set:
        quotation.valid_until = payload.valid_until
    if "notes" in payload.model_fields_set:
        quotation.notes = payload.notes
    _commit(db)
    return _load_quotation(db, quotation.id)


@router.post("/{quotation_id}/send", response_model=QuotationResponse)
def send_quotation(quotation_id: int, user: User = Depends(manage_quotations), db: Session = Depends(get_db)):
    return _transition(db, quotation_id, user, QuotationStatus.SENT)


@router.post("/{quotation_id}/accept", response_model=QuotationResponse)
def accept_quotation(quotation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _transition(db, quotation_id, user, QuotationStatus.ACCEPTED)


@router.post("/{quotation_id}/reject", response_model=QuotationResponse)
def reject_quotation(quotation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _transition(db, quotation_id, user, QuotationStatus.REJECTED)


@router.post("/{quotation_id}/cancel", response_model=QuotationResponse)
def cancel_quotation(quotation_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _transition(db, quotation_id, user, QuotationStatus.CANCELLED)
