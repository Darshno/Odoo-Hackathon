"""add invoices discounts and payments

Revision ID: 0006_billing
Revises: 0005_subscriptions
"""
from alembic import op
import sqlalchemy as sa

revision = "0006_billing"
down_revision = "0005_subscriptions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    invoice_status = sa.Enum("DRAFT", "ISSUED", "PARTIALLY_PAID", "PAID", "OVERDUE", "VOID", name="invoicestatus", native_enum=False)
    discount_type = sa.Enum("FIXED", "PERCENTAGE", name="discounttype", native_enum=False)
    payment_status = sa.Enum("RECORDED", "CONFIRMED", "VOID", name="paymentstatus", native_enum=False)
    op.create_table(
        "invoices",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_number", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("subscription_id", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", invoice_status, nullable=False, server_default="ISSUED"),
        sa.Column("issue_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=False),
        sa.Column("billing_period_start", sa.Date(), nullable=False),
        sa.Column("billing_period_end", sa.Date(), nullable=False),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_total", sa.Numeric(12, 2), nullable=False),
        sa.Column("total", sa.Numeric(12, 2), nullable=False),
        sa.Column("amount_paid", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("amount_due", sa.Numeric(12, 2), nullable=False),
        sa.Column("payment_terms", sa.String(500), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["subscription_id"], ["subscriptions.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("invoice_number", name="uq_invoices_number"),
        sa.UniqueConstraint("subscription_id", "billing_period_start", "billing_period_end", name="uq_invoice_subscription_period"),
        sa.CheckConstraint("billing_period_end >= billing_period_start", name="ck_invoice_period_order"),
        sa.CheckConstraint("due_date >= issue_date", name="ck_invoice_due_date"),
        sa.CheckConstraint("subtotal >= 0 AND discount_total >= 0 AND tax_total >= 0 AND total >= 0", name="ck_invoice_nonnegative_totals"),
        sa.CheckConstraint("amount_paid >= 0 AND amount_due >= 0 AND amount_paid + amount_due = total", name="ck_invoice_balance"),
    )
    for name, columns in (
        ("ix_invoices_customer_id", ["customer_id"]), ("ix_invoices_subscription_id", ["subscription_id"]),
        ("ix_invoices_status", ["status"]), ("ix_invoices_due_date", ["due_date"]),
        ("ix_invoices_customer_status", ["customer_id", "status"]),
    ):
        op.create_index(name, "invoices", columns)
    op.create_table(
        "invoice_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("subscription_line_id", sa.Integer(), nullable=True),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(160), nullable=False),
        sa.Column("variant_name", sa.String(160), nullable=True),
        sa.Column("plan_name", sa.String(160), nullable=False),
        sa.Column("sku", sa.String(80), nullable=True),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("period_start", sa.Date(), nullable=False),
        sa.Column("period_end", sa.Date(), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_subtotal", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["subscription_line_id"], ["subscription_lines.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="SET NULL"),
        sa.CheckConstraint("period_end >= period_start", name="ck_invoice_line_period_order"),
        sa.CheckConstraint("quantity > 0", name="ck_invoice_line_quantity"),
        sa.CheckConstraint("unit_price >= 0 AND line_subtotal >= 0 AND discount_amount >= 0 AND tax_amount >= 0 AND line_total >= 0", name="ck_invoice_line_nonnegative_amounts"),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])
    op.create_table(
        "discounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("discount_type", discount_type, nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=True),
        sa.Column("starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("minimum_subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("usage_limit", sa.Integer(), nullable=True),
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("code", name="uq_discounts_code"),
        sa.CheckConstraint("value > 0 AND minimum_subtotal >= 0 AND usage_count >= 0", name="ck_discount_values"),
    )
    op.create_index("ix_discounts_active", "discounts", ["is_active"])
    op.create_index("ix_discounts_active_window", "discounts", ["is_active", "starts_at", "expires_at"])
    op.create_table(
        "invoice_discounts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("discount_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("discount_type", discount_type, nullable=False),
        sa.Column("value", sa.Numeric(12, 2), nullable=False),
        sa.Column("discount_amount", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["discount_id"], ["discounts.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("invoice_id", name="uq_invoice_one_discount"),
    )
    op.create_table(
        "payments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_number", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("status", payment_status, nullable=False, server_default="CONFIRMED"),
        sa.Column("payment_method", sa.String(40), nullable=False),
        sa.Column("external_reference", sa.String(160), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("payment_number", name="uq_payments_number"),
        sa.CheckConstraint("amount > 0", name="ck_payment_positive_amount"),
    )
    op.create_index("ix_payments_customer_id", "payments", ["customer_id"])
    op.create_index("ix_payments_status", "payments", ["status"])
    op.create_index("ix_payments_customer_status", "payments", ["customer_id", "status"])
    op.create_table(
        "payment_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("payment_id", sa.Integer(), nullable=False),
        sa.Column("invoice_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["payment_id"], ["payments.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invoice_id"], ["invoices.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("payment_id", "invoice_id", name="uq_payment_invoice_allocation"),
        sa.CheckConstraint("amount > 0", name="ck_payment_allocation_positive_amount"),
    )


def downgrade() -> None:
    op.drop_table("payment_allocations")
    op.drop_index("ix_payments_customer_status", table_name="payments")
    op.drop_index("ix_payments_status", table_name="payments")
    op.drop_index("ix_payments_customer_id", table_name="payments")
    op.drop_table("payments")
    op.drop_table("invoice_discounts")
    op.drop_index("ix_discounts_active_window", table_name="discounts")
    op.drop_index("ix_discounts_active", table_name="discounts")
    op.drop_table("discounts")
    op.drop_index("ix_invoice_lines_invoice_id", table_name="invoice_lines")
    op.drop_table("invoice_lines")
    for name in ("ix_invoices_customer_status", "ix_invoices_due_date", "ix_invoices_status", "ix_invoices_subscription_id", "ix_invoices_customer_id"):
        op.drop_index(name, table_name="invoices")
    op.drop_table("invoices")
