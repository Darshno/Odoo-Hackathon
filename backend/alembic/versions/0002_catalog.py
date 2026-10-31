"""add products, variants, and subscription plans

Revision ID: 0002_catalog
Revises: 0001_initial
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_catalog"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("product_type", sa.String(80), nullable=False, server_default="SERVICE"),
        sa.Column("sku", sa.String(80), nullable=True),
        sa.Column("sales_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=False, server_default="0"),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("internal_notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_products_is_active", "products", ["is_active"])
    op.create_foreign_key("fk_products_created_by", "products", "users", ["created_by"], ["id"], ondelete="SET NULL")
    op.create_index("ix_products_created_by", "products", ["created_by"])
    op.create_index("uq_products_sku", "products", ["sku"], unique=True)
    op.create_table(
        "product_variants",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("sku", sa.String(80), nullable=False),
        sa.Column("sales_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("cost_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("attributes", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("product_id", "sku", name="uq_product_variant_sku"),
    )
    op.create_index("ix_product_variants_product_id", "product_variants", ["product_id"])
    op.create_table(
        "subscription_plans",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), nullable=False),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sales_price", sa.Numeric(12, 2), nullable=False),
        sa.Column("minimum_quantity", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("billing_interval", sa.String(20), nullable=False),
        sa.Column("available_from", sa.DateTime(timezone=True), nullable=True),
        sa.Column("available_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("pause_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("renewal_allowed", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("early_closure_allowed", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("auto_close_enabled", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="RESTRICT"),
        sa.UniqueConstraint("product_id", "name", name="uq_subscription_plan_name"),
    )
    op.create_index("ix_subscription_plans_product_id", "subscription_plans", ["product_id"])
    op.create_index("ix_subscription_plans_variant_id", "subscription_plans", ["variant_id"])
    op.create_index("ix_subscription_plans_is_active", "subscription_plans", ["is_active"])


def downgrade() -> None:
    op.drop_table("subscription_plans")
    op.drop_table("product_variants")
    op.drop_index("ix_products_created_by", table_name="products")
    op.drop_index("uq_products_sku", table_name="products")
    op.drop_constraint("fk_products_created_by", "products", type_="foreignkey")
    op.drop_table("products")
