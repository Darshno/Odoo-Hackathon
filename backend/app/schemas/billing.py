from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.billing import DiscountType, InvoiceStatus, PaymentStatus
from app.schemas.catalog import Page
from app.schemas.quotation import CustomerSummary


class InvoiceLineResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    subscription_line_id: int | None
    plan_id: int | None
    product_id: int | None
    variant_id: int | None
    product_name: str
    variant_name: str | None
    plan_name: str
    sku: str | None
    billing_interval: str
    period_start: date
    period_end: date
    quantity: int
    currency: str
    unit_price: Decimal
    line_subtotal: Decimal
    discount_amount: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    line_total: Decimal


class InvoiceDiscountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    code: str
    discount_type: DiscountType
    value: Decimal
    discount_amount: Decimal


class PaymentAllocationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    invoice_id: int
    amount: Decimal


class PaymentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    payment_number: str
    customer_id: int
    amount: Decimal
    currency: str
    status: PaymentStatus
    payment_method: str
    external_reference: str | None
    received_at: datetime
    notes: str | None
    allocations: list[PaymentAllocationResponse]
    created_at: datetime
    updated_at: datetime


class InvoiceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    invoice_number: str
    customer_id: int
    customer: CustomerSummary
    subscription_id: int
    currency: str
    status: InvoiceStatus
    issue_date: date
    due_date: date
    billing_period_start: date
    billing_period_end: date
    subtotal: Decimal
    discount_total: Decimal
    tax_total: Decimal
    total: Decimal
    amount_paid: Decimal
    amount_due: Decimal
    payment_terms: str | None
    notes: str | None
    lines: list[InvoiceLineResponse]
    discounts: list[InvoiceDiscountResponse]
    payments: list[PaymentAllocationResponse]
    created_at: datetime
    updated_at: datetime


class InvoicePage(Page[InvoiceResponse]):
    pass


class InvoiceGenerateRequest(BaseModel):
    discount_id: int | None = Field(default=None, gt=0)
    issue_immediately: bool = True


class PaymentCreate(BaseModel):
    invoice_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, decimal_places=2, max_digits=12)
    currency: str = Field(min_length=3, max_length=3)
    payment_method: str = Field(min_length=1, max_length=40)
    external_reference: str | None = Field(default=None, max_length=160)
    received_at: datetime | None = None
    notes: str | None = Field(default=None, max_length=5000)


class PaymentPage(Page[PaymentResponse]):
    pass


class DiscountCreate(BaseModel):
    code: str = Field(min_length=1, max_length=80)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=5000)
    discount_type: DiscountType
    value: Decimal = Field(gt=0, decimal_places=2, max_digits=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    starts_at: datetime | None = None
    expires_at: datetime | None = None
    minimum_subtotal: Decimal = Field(default=0, ge=0, decimal_places=2, max_digits=12)
    usage_limit: int | None = Field(default=None, ge=1)
    is_active: bool = True

    @model_validator(mode="after")
    def validate_discount(self):
        if self.discount_type == DiscountType.FIXED and self.currency is None:
            raise ValueError("Fixed discounts require a currency.")
        if self.discount_type == DiscountType.PERCENTAGE and self.value > 100:
            raise ValueError("Percentage discounts cannot exceed 100.")
        if self.expires_at and self.starts_at and self.expires_at < self.starts_at:
            raise ValueError("expires_at must be after starts_at.")
        return self


class DiscountResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    code: str
    name: str
    description: str | None
    discount_type: DiscountType
    value: Decimal
    currency: str | None
    starts_at: datetime | None
    expires_at: datetime | None
    minimum_subtotal: Decimal
    usage_limit: int | None
    usage_count: int
    is_active: bool
