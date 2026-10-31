"""add subscriptions and historical subscription lines

Revision ID: 0005_subscriptions
Revises: 0004_quotation_templates
"""
from alembic import op
import sqlalchemy as sa


revision = "0005_subscriptions"
down_revision = "0004_quotation_templates"
branch_labels = None
depends_on = None


def upgrade() -> None:
    subscription_status = sa.Enum("ACTIVE", "PAUSED", "CLOSED", name="subscriptionstatus", native_enum=False)
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subscription_number", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("status", subscription_status, nullable=False, server_default="ACTIVE"),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=True),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("next_billing_date", sa.Date(), nullable=True),
        sa.Column("last_billing_date", sa.Date(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("subscription_number", name="uq_subscriptions_number"),
        sa.UniqueConstraint("quotation_id", name="uq_subscriptions_quotation"),
    )
    op.create_index("ix_subscriptions_customer_id", "subscriptions", ["customer_id"])
    op.create_index("ix_subscriptions_quotation_id", "subscriptions", ["quotation_id"])
    op.create_index("ix_subscriptions_status", "subscriptions", ["status"])
    op.create_index("ix_subscriptions_next_billing_date", "subscriptions", ["next_billing_date"])
    op.create_index("ix_subscriptions_customer_status", "subscriptions", ["customer_id", "status"])
    op.create_table(
        "subscription_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(160), nullable=False),
        sa.Column("variant_name", sa.String(160), nullable=True),
        sa.Column("plan_name", sa.String(160), nullable=False),
        sa.Column("sku", sa.String(80), nullable=True),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("renewal_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("pause_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_subscription_lines_subscription_id", "subscription_lines", ["subscription_id"])


def downgrade() -> None:
    op.drop_index("ix_subscription_lines_subscription_id", table_name="subscription_lines")
    op.drop_table("subscription_lines")
    op.drop_index("ix_subscriptions_customer_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_next_billing_date", table_name="subscriptions")
    op.drop_index("ix_subscriptions_status", table_name="subscriptions")
    op.drop_index("ix_subscriptions_quotation_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_customer_id", table_name="subscriptions")
    op.drop_table("subscriptions")
