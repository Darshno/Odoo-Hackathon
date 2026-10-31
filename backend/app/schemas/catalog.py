from datetime import datetime
from decimal import Decimal
from typing import Generic, TypeVar

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.models.catalog import BillingInterval

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    items: list[T]
    page: int
    page_size: int
    total: int
    pages: int


class VariantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    sku: str = Field(min_length=1, max_length=80)
    sales_price: Decimal = Field(default=0, ge=0, decimal_places=2, max_digits=12)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    cost_price: Decimal = Field(default=0, ge=0, decimal_places=2, max_digits=12)
    attributes: dict = Field(default_factory=dict)
    is_active: bool = True

    @model_validator(mode="after")
    def legacy_price(self):
        if self.price is not None and self.sales_price == 0:
            self.sales_price = self.price
        return self


class VariantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    sku: str | None = Field(default=None, min_length=1, max_length=80)
    sales_price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    cost_price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    attributes: dict | None = None
    is_active: bool | None = None


class VariantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    name: str
    sku: str
    sales_price: Decimal
    cost_price: Decimal | None = None
    attributes: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    product_type: str = Field(default="SERVICE", min_length=1, max_length=80)
    sku: str | None = Field(default=None, max_length=80)
    sales_price: Decimal = Field(default=0, ge=0, decimal_places=2, max_digits=12)
    cost_price: Decimal = Field(default=0, ge=0, decimal_places=2, max_digits=12)
    currency: str = Field(default="USD", min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=2000)
    internal_notes: str | None = Field(default=None, max_length=5000)
    is_active: bool = True
    variants: list[VariantCreate] = Field(default_factory=list)

    @field_validator("name")
    @classmethod
    def clean_name(cls, value: str) -> str:
        return " ".join(value.strip().split())


class ProductUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=160)
    product_type: str | None = Field(default=None, min_length=1, max_length=80)
    sku: str | None = Field(default=None, max_length=80)
    sales_price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    cost_price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    description: str | None = Field(default=None, max_length=2000)
    internal_notes: str | None = Field(default=None, max_length=5000)
    is_active: bool | None = None


class ProductResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    product_type: str
    sku: str | None
    sales_price: Decimal
    cost_price: Decimal | None = None
    currency: str
    description: str | None
    internal_notes: str | None = None
    created_by: int | None
    is_active: bool
    variants: list[VariantResponse] = []
    created_at: datetime
    updated_at: datetime


class PlanCreate(BaseModel):
    product_id: int = Field(gt=0)
    variant_id: int | None = Field(default=None, gt=0)
    name: str = Field(min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    sales_price: Decimal = Field(default=0, ge=0, decimal_places=2, max_digits=12)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    minimum_quantity: int = Field(default=1, ge=1)
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    available_from: datetime | None = None
    available_until: datetime | None = None
    pause_allowed: bool = False
    renewal_allowed: bool = True
    early_closure_allowed: bool = False
    auto_close_enabled: bool = False
    is_active: bool = True

    @model_validator(mode="after")
    def legacy_price(self):
        if self.price is not None and self.sales_price == 0:
            self.sales_price = self.price
        return self

    @field_validator("available_until")
    @classmethod
    def valid_dates(cls, value, info):
        start = info.data.get("available_from")
        if value and start and value < start:
            raise ValueError("available_until must be after available_from")
        return value


class PlanUpdate(BaseModel):
    product_id: int | None = Field(default=None, gt=0)
    variant_id: int | None = Field(default=None, gt=0)
    name: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = Field(default=None, max_length=2000)
    sales_price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    price: Decimal | None = Field(default=None, ge=0, decimal_places=2, max_digits=12)
    minimum_quantity: int | None = Field(default=None, ge=1)
    billing_interval: BillingInterval | None = None
    available_from: datetime | None = None
    available_until: datetime | None = None
    pause_allowed: bool | None = None
    renewal_allowed: bool | None = None
    early_closure_allowed: bool | None = None
    auto_close_enabled: bool | None = None
    is_active: bool | None = None

    @model_validator(mode="after")
    def legacy_price(self):
        if self.price is not None and self.sales_price is None:
            self.sales_price = self.price
        return self


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    variant_id: int | None
    name: str
    description: str | None
    sales_price: Decimal
    minimum_quantity: int
    billing_interval: BillingInterval
    available_from: datetime | None
    available_until: datetime | None
    pause_allowed: bool
    renewal_allowed: bool
    early_closure_allowed: bool
    auto_close_enabled: bool
    is_active: bool
    created_at: datetime
    updated_at: datetime
