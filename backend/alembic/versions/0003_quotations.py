"""add quotations and quotation lines

Revision ID: 0003_quotations
Revises: 0002_catalog
"""
from alembic import op
import sqlalchemy as sa


revision = "0003_quotations"
down_revision = "0002_catalog"
branch_labels = None
depends_on = None


def upgrade() -> None:
    quotation_status = sa.Enum(
        "DRAFT", "SENT", "ACCEPTED", "REJECTED", "EXPIRED", "CANCELLED",
        name="quotationstatus", native_enum=False,
    )
    op.create_table(
        "quotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quotation_number", sa.String(32), nullable=False),
        sa.Column("customer_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("status", quotation_status, nullable=False, server_default="DRAFT"),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("valid_until", sa.Date(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("subtotal", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("total", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["customer_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("quotation_number", name="uq_quotations_number"),
    )
    op.create_index("ix_quotations_customer_id", "quotations", ["customer_id"])
    op.create_index("ix_quotations_created_by", "quotations", ["created_by"])
    op.create_index("ix_quotations_status", "quotations", ["status"])
    op.create_index("ix_quotations_customer_status", "quotations", ["customer_id", "status"])
    op.create_table(
        "quotation_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("quotation_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("product_name", sa.String(160), nullable=False),
        sa.Column("variant_name", sa.String(160), nullable=True),
        sa.Column("plan_name", sa.String(160), nullable=False),
        sa.Column("sku", sa.String(80), nullable=True),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("line_total", sa.Numeric(12, 2), nullable=False),
        sa.ForeignKeyConstraint(["quotation_id"], ["quotations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_quotation_lines_quotation_id", "quotation_lines", ["quotation_id"])


def downgrade() -> None:
    op.drop_index("ix_quotation_lines_quotation_id", table_name="quotation_lines")
    op.drop_table("quotation_lines")
    op.drop_index("ix_quotations_customer_status", table_name="quotations")
    op.drop_index("ix_quotations_status", table_name="quotations")
    op.drop_index("ix_quotations_created_by", table_name="quotations")
    op.drop_index("ix_quotations_customer_id", table_name="quotations")
    op.drop_table("quotations")
