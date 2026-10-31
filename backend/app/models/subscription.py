import enum
from datetime import date
from decimal import Decimal

from sqlalchemy import Boolean, Date, Enum, ForeignKey, Index, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class SubscriptionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    CLOSED = "CLOSED"


class Subscription(TimestampMixin, Base):
    __tablename__ = "subscriptions"
    __table_args__ = (
        UniqueConstraint("subscription_number", name="uq_subscriptions_number"),
        UniqueConstraint("quotation_id", name="uq_subscriptions_quotation"),
        Index("ix_subscriptions_customer_status", "customer_id", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_number: Mapped[str] = mapped_column(String(32), nullable=False, unique=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    quotation_id: Mapped[int] = mapped_column(ForeignKey("quotations.id", ondelete="RESTRICT"), nullable=False, unique=True, index=True)
    status: Mapped[SubscriptionStatus] = mapped_column(
        Enum(SubscriptionStatus, native_enum=False), nullable=False, default=SubscriptionStatus.ACTIVE, index=True
    )
    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    next_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    last_billing_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    customer = relationship("User", foreign_keys=[customer_id])
    quotation = relationship("Quotation", foreign_keys=[quotation_id])
    lines: Mapped[list["SubscriptionLine"]] = relationship(
        back_populates="subscription", cascade="all, delete-orphan", order_by="SubscriptionLine.id"
    )


class SubscriptionLine(Base):
    __tablename__ = "subscription_lines"
    __table_args__ = (Index("ix_subscription_lines_subscription_id", "subscription_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    subscription_id: Mapped[int] = mapped_column(ForeignKey("subscriptions.id", ondelete="CASCADE"), nullable=False)
    plan_id: Mapped[int | None] = mapped_column(ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id", ondelete="SET NULL"), nullable=True)
    variant_id: Mapped[int | None] = mapped_column(ForeignKey("product_variants.id", ondelete="SET NULL"), nullable=True)
    product_name: Mapped[str] = mapped_column(String(160), nullable=False)
    variant_name: Mapped[str | None] = mapped_column(String(160), nullable=True)
    plan_name: Mapped[str] = mapped_column(String(160), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(80), nullable=True)
    billing_interval: Mapped[str] = mapped_column(String(20), nullable=False)
    renewal_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    pause_allowed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quantity: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    tax_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=0)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    subscription: Mapped[Subscription] = relationship(back_populates="lines")
