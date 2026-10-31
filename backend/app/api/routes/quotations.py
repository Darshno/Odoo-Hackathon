from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.catalog import Product, ProductVariant, SubscriptionPlan
from app.models.quotation import (
    Quotation, QuotationLine, QuotationStatus, QuotationTemplate, QuotationTemplateLine,
)
from app.models.user import User, UserRole
from app.schemas.quotation import (
    QuotationCreate, QuotationFromTemplateCreate, QuotationPage, QuotationResponse, QuotationTemplateCreate,
    QuotationTemplatePage, QuotationTemplateResponse, QuotationTemplateUpdate, QuotationUpdate,
)

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
    if quotation.valid_until and quotation.valid_until < date.today() and quotation.status in {
        QuotationStatus.DRAFT, QuotationStatus.SENT,
    }:
        quotation.status = QuotationStatus.EXPIRED
        db.commit()
    return quotation


def _ensure_customer(db: Session, customer_id: int) -> User:
    customer = db.get(User, customer_id)
    if not customer or customer.role != UserRole.CUSTOMER or not customer.is_active:
        raise HTTPException(422, "Quotation customer must be an active CUSTOMER account.")
    return customer


def _build_lines(db: Session, payload_lines) -> tuple[list[QuotationLine], str, Decimal, Decimal]:
    lines: list[QuotationLine] = []
    currency: str | None = None
    subtotal = Decimal("0")
    tax_total = Decimal("0")
    for payload in payload_lines:
        plan_id = payload["plan_id"] if isinstance(payload, dict) else payload.plan_id
        quantity = payload["quantity"] if isinstance(payload, dict) else payload.quantity
        plan = db.scalar(
            select(SubscriptionPlan)
            .options(joinedload(SubscriptionPlan.product), joinedload(SubscriptionPlan.variant))
            .where(SubscriptionPlan.id == plan_id)
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
        line_total = _money(unit_price * quantity)
        tax_rate = Decimal(str(getattr(payload, "tax_rate", payload.get("tax_rate", 0) if isinstance(payload, dict) else 0)))
        tax_amount = _money(line_total * tax_rate / Decimal("100"))
        amount = _money(line_total + tax_amount)
        subtotal += line_total
        tax_total += tax_amount
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
                quantity=quantity,
                unit_price=unit_price,
                line_total=line_total,
                tax_rate=tax_rate,
                tax_amount=tax_amount,
                amount=amount,
            )
        )
    return lines, currency or "USD", _money(subtotal), _money(tax_total)


def _validate_template_lines(db: Session, payload_lines) -> list[QuotationTemplateLine]:
    result = []
    for payload in payload_lines:
        if payload.plan_id:
            plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.id == payload.plan_id))
            if not plan or not plan.is_active:
                raise HTTPException(422, "Template plan must be active.")
            if payload.product_id and payload.product_id != plan.product_id:
                raise HTTPException(422, "Template product must match the selected plan.")
            if payload.variant_id and payload.variant_id != plan.variant_id:
                raise HTTPException(422, "Template variant must match the selected plan.")
            product_id = plan.product_id
            variant_id = plan.variant_id
        else:
            product = db.get(Product, payload.product_id)
            if not product or not product.is_active:
                raise HTTPException(422, "Template product must be active.")
            variant_id = payload.variant_id
            if variant_id:
                variant = db.get(ProductVariant, variant_id)
                if not variant or variant.product_id != product.id or not variant.is_active:
                    raise HTTPException(422, "Template variant must belong to the active product.")
            product_id = product.id
        result.append(QuotationTemplateLine(
            plan_id=payload.plan_id, product_id=product_id, variant_id=variant_id, quantity=payload.quantity,
        ))
    return result


def _build_product_template_line(db: Session, line: QuotationTemplateLine) -> tuple[QuotationLine, str, Decimal, Decimal]:
    product = db.get(Product, line.product_id)
    if not product or not product.is_active:
        raise HTTPException(422, "Template product must be active.")
    variant = db.get(ProductVariant, line.variant_id) if line.variant_id else None
    if line.variant_id and (not variant or variant.product_id != product.id or not variant.is_active):
        raise HTTPException(422, "Template variant must belong to the active product.")
    unit_price = _money(Decimal(product.sales_price) + (Decimal(variant.sales_price) if variant else Decimal("0")))
    line_total = _money(unit_price * line.quantity)
    quotation_line = QuotationLine(
        product_id=product.id, variant_id=variant.id if variant else None,
        product_name=product.name, variant_name=variant.name if variant else None,
        plan_name=product.name, sku=variant.sku if variant else product.sku,
        billing_interval="ONE_TIME", quantity=line.quantity, unit_price=unit_price,
        line_total=line_total, tax_rate=Decimal("0"), tax_amount=Decimal("0"), amount=line_total,
    )
    return quotation_line, product.currency, line_total, Decimal("0")


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
        raise HTTPException(403, "Only the quotation customer can accept or reject a quotation.")
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
    lines, currency, subtotal, tax_total = _build_lines(db, payload.lines)
    valid_until = payload.valid_until
    if payload.validity_days is not None:
        valid_until = date.today() + timedelta(days=payload.validity_days)
    if valid_until and payload.start_date and valid_until < payload.start_date:
        raise HTTPException(422, "valid_until must be on or after start_date.")
    quotation = Quotation(
        customer_id=customer.id,
        created_by=user.id,
        quotation_number="PENDING",
        currency=currency,
        valid_until=valid_until,
        validity_days=payload.validity_days,
        start_date=payload.start_date,
        payment_terms=payload.payment_terms,
        notes=payload.notes,
        subtotal=subtotal,
        tax_total=tax_total,
        total=_money(subtotal + tax_total),
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


@router.get("/templates", response_model=QuotationTemplatePage)
def list_templates(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    include_inactive: bool = False,
    _user: User = Depends(manage_quotations),
    db: Session = Depends(get_db),
):
    filters = [] if include_inactive else [QuotationTemplate.is_active.is_(True)]
    query = select(QuotationTemplate).options(joinedload(QuotationTemplate.lines))
    count = select(func.count(QuotationTemplate.id))
    if filters:
        query = query.where(*filters)
        count = count.where(*filters)
    total = db.scalar(count) or 0
    items = db.scalars(
        query.order_by(QuotationTemplate.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    ).unique().all()
    return QuotationTemplatePage(items=items, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.post("/templates", response_model=QuotationTemplateResponse, status_code=status.HTTP_201_CREATED)
def create_template(
    payload: QuotationTemplateCreate, user: User = Depends(manage_quotations), db: Session = Depends(get_db)
):
    template = QuotationTemplate(
        name=payload.name.strip(), description=payload.description, validity_days=payload.validity_days,
        created_by=user.id, lines=_validate_template_lines(db, payload.lines),
    )
    db.add(template)
    _commit(db)
    return db.scalar(select(QuotationTemplate).options(joinedload(QuotationTemplate.lines)).where(QuotationTemplate.id == template.id))


@router.get("/templates/{template_id}", response_model=QuotationTemplateResponse)
def get_template(template_id: int, _user: User = Depends(manage_quotations), db: Session = Depends(get_db)):
    template = db.scalar(
        select(QuotationTemplate).options(joinedload(QuotationTemplate.lines)).where(QuotationTemplate.id == template_id)
    )
    if not template:
        raise HTTPException(404, "Quotation template not found.")
    return template


@router.patch("/templates/{template_id}", response_model=QuotationTemplateResponse)
def update_template(
    template_id: int, payload: QuotationTemplateUpdate, _user: User = Depends(manage_quotations), db: Session = Depends(get_db)
):
    template = db.get(QuotationTemplate, template_id)
    if not template:
        raise HTTPException(404, "Quotation template not found.")
    values = payload.model_dump(exclude_unset=True, exclude={"lines"})
    for key, value in values.items():
        setattr(template, key, value.strip() if isinstance(value, str) and key == "name" else value)
    if payload.lines is not None:
        template.lines = _validate_template_lines(db, payload.lines)
    _commit(db)
    return db.scalar(select(QuotationTemplate).options(joinedload(QuotationTemplate.lines)).where(QuotationTemplate.id == template.id))


@router.patch("/templates/{template_id}/status", response_model=QuotationTemplateResponse)
def template_status(
    template_id: int, is_active: bool, _user: User = Depends(manage_quotations), db: Session = Depends(get_db)
):
    template = db.get(QuotationTemplate, template_id)
    if not template:
        raise HTTPException(404, "Quotation template not found.")
    template.is_active = is_active
    _commit(db)
    return db.scalar(select(QuotationTemplate).options(joinedload(QuotationTemplate.lines)).where(QuotationTemplate.id == template.id))


@router.post("/from-template", response_model=QuotationResponse, status_code=status.HTTP_201_CREATED)
def create_from_template(
    payload: QuotationFromTemplateCreate, user: User = Depends(manage_quotations), db: Session = Depends(get_db)
):
    template = db.scalar(
        select(QuotationTemplate).options(joinedload(QuotationTemplate.lines)).where(QuotationTemplate.id == payload.template_id)
    )
    if not template or not template.is_active:
        raise HTTPException(422, "Quotation template must be active.")
    customer = _ensure_customer(db, payload.customer_id)
    plan_lines = []
    direct_lines: list[QuotationLine] = []
    direct_currency: str | None = None
    direct_subtotal = Decimal("0")
    for line in template.lines:
        if line.plan_id:
            plan_lines.append({"plan_id": line.plan_id, "quantity": line.quantity, "tax_rate": Decimal("0")})
        else:
            direct_line, line_currency, line_total, _ = _build_product_template_line(db, line)
            if direct_currency and direct_currency != line_currency:
                raise HTTPException(422, "All quotation lines must use the same currency.")
            direct_currency = line_currency
            direct_subtotal += line_total
            direct_lines.append(direct_line)
    lines, currency, subtotal, tax_total = _build_lines(db, plan_lines) if plan_lines else ([], direct_currency or "USD", Decimal("0"), Decimal("0"))
    if direct_lines:
        if lines and currency != direct_currency:
            raise HTTPException(422, "All quotation lines must use the same currency.")
        lines.extend(direct_lines)
        subtotal = _money(subtotal + direct_subtotal)
    start_date = payload.start_date
    valid_until = (start_date or date.today()) + timedelta(days=template.validity_days)
    quotation = Quotation(
        customer_id=customer.id, created_by=user.id, template_id=template.id, quotation_number="PENDING",
        currency=currency, valid_until=valid_until, validity_days=template.validity_days,
        start_date=start_date, payment_terms=payload.payment_terms, notes=payload.notes,
        subtotal=subtotal, tax_total=tax_total, total=_money(subtotal + tax_total), lines=lines,
    )
    db.add(quotation)
    db.flush()
    quotation.quotation_number = f"Q-{datetime.now(timezone.utc).year}-{quotation.id:06d}"
    _commit(db)
    return _load_quotation(db, quotation.id)


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
        lines, currency, subtotal, tax_total = _build_lines(db, payload.lines)
        if currency != quotation.currency:
            raise HTTPException(422, "Updated quotation lines must use the existing quotation currency.")
        quotation.lines = lines
        quotation.subtotal = subtotal
        quotation.tax_total = tax_total
        quotation.total = _money(subtotal + tax_total)
    if "valid_until" in payload.model_fields_set:
        quotation.valid_until = payload.valid_until
    if "notes" in payload.model_fields_set:
        quotation.notes = payload.notes
    if "validity_days" in payload.model_fields_set:
        quotation.validity_days = payload.validity_days
        if payload.validity_days is not None:
            quotation.valid_until = (quotation.start_date or date.today()) + timedelta(days=payload.validity_days)
    if "start_date" in payload.model_fields_set:
        quotation.start_date = payload.start_date
    if "payment_terms" in payload.model_fields_set:
        quotation.payment_terms = payload.payment_terms
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
