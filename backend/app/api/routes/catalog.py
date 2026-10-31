from datetime import datetime, timezone
from math import ceil

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.dependencies import get_current_user, require_roles
from app.db.session import get_db
from app.models.catalog import Product, ProductVariant, SubscriptionPlan
from app.models.user import User, UserRole
from app.schemas.catalog import (
    Page, PlanCreate, PlanResponse, PlanUpdate, ProductCreate, ProductResponse,
    ProductUpdate, VariantCreate, VariantResponse, VariantUpdate,
)

router = APIRouter(tags=["Catalog"])
manage_catalog = require_roles(UserRole.ADMIN, UserRole.STAFF)


def _product(product, public=False):
    data = ProductResponse.model_validate(product).model_dump()
    if public:
        data["cost_price"] = None
        data["internal_notes"] = None
        for variant in data["variants"]:
            variant["cost_price"] = None
    return data


def _page_params(page: int, page_size: int):
    return (page - 1) * page_size, page_size


@router.get("/products", response_model=Page[ProductResponse])
def list_products(
    page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100),
    search: str | None = None, is_active: bool | None = None,
    sort: str = Query("created_at", pattern="^(created_at|name|sales_price)$"),
    include_inactive: bool = Query(False), _user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    public = _user.role == UserRole.CUSTOMER
    query = select(Product).options(selectinload(Product.variants))
    count = select(func.count(Product.id))
    filters = []
    if public or not include_inactive:
        filters.append(Product.is_active.is_(True))
    elif is_active is not None:
        filters.append(Product.is_active == is_active)
    if public:
        filters.append(Product.is_active.is_(True))
    if search:
        term = f"%{search.strip()}%"
        filters.append(or_(Product.name.ilike(term), Product.sku.ilike(term), Product.product_type.ilike(term)))
    if filters:
        query = query.where(*filters); count = count.where(*filters)
    order = {"name": Product.name, "sales_price": Product.sales_price, "created_at": Product.created_at}[sort]
    offset, limit = _page_params(page, page_size)
    total = db.scalar(count) or 0
    products = db.scalars(query.order_by(order.desc()).offset(offset).limit(limit)).unique().all()
    return Page(items=[_product(p, public) for p in products], page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


def _commit(db, conflict: str):
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, conflict) from exc


@router.post("/products", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(payload: ProductCreate, user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    product = Product(**payload.model_dump(exclude={"variants"}), created_by=user.id)
    product.variants = [ProductVariant(**v.model_dump(exclude={"price"})) for v in payload.variants]
    db.add(product); _commit(db, "Product or variant SKU already exists.")
    db.refresh(product)
    return product


@router.get("/products/{product_id}", response_model=ProductResponse)
def get_product(product_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.scalar(select(Product).options(selectinload(Product.variants)).where(Product.id == product_id))
    if not product or (user.role == UserRole.CUSTOMER and not product.is_active):
        raise HTTPException(404, "Product not found.")
    return _product(product, user.role == UserRole.CUSTOMER)


@router.patch("/products/{product_id}", response_model=ProductResponse)
def update_product(product_id: int, payload: ProductUpdate, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product: raise HTTPException(404, "Product not found.")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(product, key, value)
    _commit(db, "Product SKU already exists.")
    return db.scalar(select(Product).options(selectinload(Product.variants)).where(Product.id == product_id))


@router.patch("/products/{product_id}/status", response_model=ProductResponse)
def product_status(product_id: int, is_active: bool, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product: raise HTTPException(404, "Product not found.")
    product.is_active = is_active; db.commit()
    return db.scalar(select(Product).options(selectinload(Product.variants)).where(Product.id == product_id))


@router.get("/products/{product_id}/variants", response_model=list[VariantResponse])
def list_variants(product_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product or (user.role == UserRole.CUSTOMER and not product.is_active): raise HTTPException(404, "Product not found.")
    variants = db.scalars(select(ProductVariant).where(ProductVariant.product_id == product_id, ProductVariant.is_active.is_(True) if user.role == UserRole.CUSTOMER else True)).all()
    return [dict(VariantResponse.model_validate(v).model_dump(), cost_price=None) if user.role == UserRole.CUSTOMER else v for v in variants]


@router.post("/products/{product_id}/variants", response_model=VariantResponse, status_code=201)
def create_variant(product_id: int, payload: VariantCreate, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    product = db.get(Product, product_id)
    if not product: raise HTTPException(404, "Product not found.")
    if not product.is_active: raise HTTPException(422, "Cannot add a variant to an inactive product.")
    variant = ProductVariant(product_id=product_id, **payload.model_dump()); db.add(variant); _commit(db, "Variant SKU already exists for this product.")
    db.refresh(variant); return variant


@router.patch("/products/{product_id}/variants/{variant_id}", response_model=VariantResponse)
def update_variant(product_id: int, variant_id: int, payload: VariantUpdate, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    variant = db.get(ProductVariant, variant_id)
    if not variant or variant.product_id != product_id: raise HTTPException(404, "Variant not found.")
    for key, value in payload.model_dump(exclude_unset=True).items(): setattr(variant, key, value)
    _commit(db, "Variant SKU already exists for this product."); db.refresh(variant); return variant


@router.patch("/products/{product_id}/variants/{variant_id}/status", response_model=VariantResponse)
def variant_status(product_id: int, variant_id: int, is_active: bool, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    variant = db.get(ProductVariant, variant_id)
    if not variant or variant.product_id != product_id: raise HTTPException(404, "Variant not found.")
    variant.is_active = is_active; db.commit(); return variant


def validate_plan(db, product_id, variant_id, start=None, end=None):
    product = db.get(Product, product_id)
    if not product or not product.is_active: raise HTTPException(422, "Plan product must be active.")
    if variant_id is not None:
        variant = db.get(ProductVariant, variant_id)
        if not variant or variant.product_id != product_id or not variant.is_active: raise HTTPException(422, "Plan variant must belong to the active product and be active.")
    if start and end and end < start: raise HTTPException(422, "available_until must be after available_from.")


@router.get("/plans", response_model=Page[PlanResponse])
def list_plans(page: int = Query(1, ge=1), page_size: int = Query(20, ge=1, le=100), search: str | None = None, is_active: bool | None = None, sort: str = Query("created_at", pattern="^(created_at|name|sales_price)$"), _user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    filters = [SubscriptionPlan.is_active.is_(True)] if _user.role == UserRole.CUSTOMER else ([] if is_active is None else [SubscriptionPlan.is_active == is_active])
    if _user.role == UserRole.CUSTOMER:
        now = datetime.now(timezone.utc)
        filters.extend([
            or_(SubscriptionPlan.available_from.is_(None), SubscriptionPlan.available_from <= now),
            or_(SubscriptionPlan.available_until.is_(None), SubscriptionPlan.available_until >= now),
        ])
    if search: filters.append(SubscriptionPlan.name.ilike(f"%{search.strip()}%"))
    query = select(SubscriptionPlan); count = select(func.count(SubscriptionPlan.id))
    if filters: query = query.where(*filters); count = count.where(*filters)
    order = {"name": SubscriptionPlan.name, "sales_price": SubscriptionPlan.sales_price, "created_at": SubscriptionPlan.created_at}[sort]
    total = db.scalar(count) or 0; offset, limit = _page_params(page, page_size)
    plans = db.scalars(query.order_by(order.desc()).offset(offset).limit(limit)).all()
    return Page(items=plans, page=page, page_size=page_size, total=total, pages=ceil(total / page_size) if total else 0)


@router.post("/plans", response_model=PlanResponse, status_code=201)
def create_plan(payload: PlanCreate, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    validate_plan(db, payload.product_id, payload.variant_id, payload.available_from, payload.available_until)
    plan = SubscriptionPlan(**payload.model_dump(exclude={"price"})); db.add(plan); _commit(db, "A plan with that name already exists for this product."); db.refresh(plan); return plan


@router.get("/plans/{plan_id}", response_model=PlanResponse)
def get_plan(plan_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan or (user.role == UserRole.CUSTOMER and not plan.is_active):
        raise HTTPException(404, "Plan not found.")
    return plan


@router.patch("/plans/{plan_id}", response_model=PlanResponse)
def update_plan(plan_id: int, payload: PlanUpdate, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found.")
    values = payload.model_dump(exclude_unset=True, exclude={"price"}); product_id = values.pop("product_id", plan.product_id)
    validate_plan(db, product_id, values.get("variant_id", plan.variant_id), values.get("available_from", plan.available_from), values.get("available_until", plan.available_until))
    for key, value in values.items(): setattr(plan, key, value)
    plan.product_id = product_id; _commit(db, "A plan with that name already exists for this product."); db.refresh(plan); return plan


@router.patch("/plans/{plan_id}/status", response_model=PlanResponse)
def plan_status(plan_id: int, is_active: bool, _user: User = Depends(manage_catalog), db: Session = Depends(get_db)):
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found.")
    plan.is_active = is_active; db.commit(); return plan


@router.delete("/products/{product_id}", status_code=409)
def prevent_product_deletion(product_id: int, _user: User = Depends(manage_catalog)):
    raise HTTPException(409, "Products are retained for auditability; deactivate instead.")


@router.delete("/products/{product_id}/variants/{variant_id}", status_code=409)
def prevent_variant_deletion(product_id: int, variant_id: int, _user: User = Depends(manage_catalog)):
    raise HTTPException(409, "Variants are retained for auditability; deactivate instead.")


@router.delete("/plans/{plan_id}", status_code=409)
def prevent_plan_deletion(plan_id: int, _user: User = Depends(manage_catalog)):
    raise HTTPException(409, "Plans are retained for auditability; deactivate instead.")
