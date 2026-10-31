from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.quotation import QuotationStatus
from app.schemas.catalog import Page


class QuotationLineCreate(BaseModel):
    plan_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1)
    tax_rate: Decimal = Field(default=0, ge=0, le=100, decimal_places=2, max_digits=5)


class QuotationCreate(BaseModel):
    customer_id: int = Field(gt=0)
    valid_until: date | None = None
    validity_days: int | None = Field(default=None, ge=1, le=3650)
    start_date: date | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[QuotationLineCreate] = Field(min_length=1)


class QuotationUpdate(BaseModel):
    valid_until: date | None = None
    validity_days: int | None = Field(default=None, ge=1, le=3650)
    start_date: date | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[QuotationLineCreate] | None = Field(default=None, min_length=1)


class CustomerSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    full_name: str
    email: str


class QuotationLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int | None
    product_id: int | None
    variant_id: int | None
    product_name: str
    variant_name: str | None
    plan_name: str
    sku: str | None
    billing_interval: str
    quantity: int
    unit_price: Decimal
    line_total: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    amount: Decimal


class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_number: str
    customer_id: int
    customer: CustomerSummary
    created_by: int | None
    template_id: int | None
    status: QuotationStatus
    currency: str
    valid_until: date | None
    start_date: date | None
    validity_days: int | None
    payment_terms: str | None
    notes: str | None
    subtotal: Decimal
    tax_total: Decimal
    total: Decimal
    lines: list[QuotationLineResponse]
    created_at: datetime
    updated_at: datetime


class QuotationPage(Page[QuotationResponse]):
    pass


class QuotationTemplateLineCreate(BaseModel):
    plan_id: int | None = Field(default=None, gt=0)
    product_id: int | None = Field(default=None, gt=0)
    variant_id: int | None = Field(default=None, gt=0)
    quantity: int = Field(default=1, ge=1)

    @model_validator(mode="after")
    def require_reference(self):
        if not self.plan_id and not self.product_id:
            raise ValueError("A template line must reference a plan or product.")
        return self


class QuotationTemplateCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    validity_days: int = Field(default=30, ge=1, le=3650)
    lines: list[QuotationTemplateLineCreate] = Field(min_length=1)


class QuotationTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    validity_days: int | None = Field(default=None, ge=1, le=3650)
    lines: list[QuotationTemplateLineCreate] | None = Field(default=None, min_length=1)


class QuotationTemplateLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    plan_id: int | None
    product_id: int | None
    variant_id: int | None
    quantity: int


class QuotationTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    description: str | None
    validity_days: int
    is_active: bool
    created_by: int | None
    lines: list[QuotationTemplateLineResponse]
    created_at: datetime
    updated_at: datetime


class QuotationTemplatePage(Page[QuotationTemplateResponse]):
    pass


class QuotationFromTemplateCreate(BaseModel):
    template_id: int = Field(gt=0)
    customer_id: int = Field(gt=0)
    start_date: date | None = None
    payment_terms: str | None = Field(default=None, max_length=500)
    notes: str | None = Field(default=None, max_length=5000)
