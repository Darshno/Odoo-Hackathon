from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.subscription import SubscriptionStatus
from app.schemas.billing import InvoiceResponse
from app.schemas.catalog import Page
from app.schemas.quotation import CustomerSummary


class PlanPurchaseRequest(BaseModel):
    quantity: int = Field(default=1, ge=1)


class SubscriptionLineResponse(BaseModel):
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
    renewal_allowed: bool
    pause_allowed: bool
    quantity: int
    currency: str
    unit_price: Decimal
    tax_rate: Decimal
    tax_amount: Decimal
    amount: Decimal


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    subscription_number: str
    customer_id: int
    customer: CustomerSummary
    quotation_id: int
    status: SubscriptionStatus
    start_date: date
    end_date: date | None
    billing_interval: str
    next_billing_date: date | None
    last_billing_date: date | None
    lines: list[SubscriptionLineResponse]
    created_at: datetime
    updated_at: datetime


class SubscriptionPage(Page[SubscriptionResponse]):
    pass


class PlanPurchaseResponse(BaseModel):
    subscription: SubscriptionResponse
    invoice: InvoiceResponse
