from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.quotation import QuotationStatus
from app.schemas.catalog import Page


class QuotationLineCreate(BaseModel):
    plan_id: int = Field(gt=0)
    quantity: int = Field(default=1, ge=1)


class QuotationCreate(BaseModel):
    customer_id: int = Field(gt=0)
    valid_until: date | None = None
    notes: str | None = Field(default=None, max_length=5000)
    lines: list[QuotationLineCreate] = Field(min_length=1)


class QuotationUpdate(BaseModel):
    valid_until: date | None = None
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


class QuotationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quotation_number: str
    customer_id: int
    customer: CustomerSummary
    created_by: int | None
    status: QuotationStatus
    currency: str
    valid_until: date | None
    notes: str | None
    subtotal: Decimal
    total: Decimal
    lines: list[QuotationLineResponse]
    created_at: datetime
    updated_at: datetime


class QuotationPage(Page[QuotationResponse]):
    pass
