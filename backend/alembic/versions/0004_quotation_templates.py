"""add quotation templates and quotation commercial fields

Revision ID: 0004_quotation_templates
Revises: 0003_quotations
"""
from alembic import op
import sqlalchemy as sa


revision = "0004_quotation_templates"
down_revision = "0003_quotations"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quotation_templates",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("validity_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("name", name="uq_quotation_templates_name"),
    )
    op.create_index("ix_quotation_templates_active", "quotation_templates", ["is_active"])
    op.create_index("ix_quotation_templates_created_by", "quotation_templates", ["created_by"])
    op.create_table(
        "quotation_template_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("template_id", sa.Integer(), nullable=False),
        sa.Column("plan_id", sa.Integer(), nullable=True),
        sa.Column("product_id", sa.Integer(), nullable=True),
        sa.Column("variant_id", sa.Integer(), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["template_id"], ["quotation_templates.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["plan_id"], ["subscription_plans.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["variant_id"], ["product_variants.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_quotation_template_lines_template_id", "quotation_template_lines", ["template_id"])
    op.add_column("quotations", sa.Column("template_id", sa.Integer(), nullable=True))
    op.add_column("quotations", sa.Column("start_date", sa.Date(), nullable=True))
    op.add_column("quotations", sa.Column("validity_days", sa.Integer(), nullable=True))
    op.add_column("quotations", sa.Column("payment_terms", sa.String(500), nullable=True))
    op.add_column("quotations", sa.Column("tax_total", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.create_foreign_key("fk_quotations_template_id", "quotations", "quotation_templates", ["template_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_quotations_template_id", "quotations", ["template_id"])
    op.add_column("quotation_lines", sa.Column("tax_rate", sa.Numeric(5, 2), nullable=False, server_default="0"))
    op.add_column("quotation_lines", sa.Column("tax_amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.add_column("quotation_lines", sa.Column("amount", sa.Numeric(12, 2), nullable=False, server_default="0"))
    op.execute("UPDATE quotation_lines SET amount = line_total WHERE amount = 0")


def downgrade() -> None:
    op.drop_column("quotation_lines", "amount")
    op.drop_column("quotation_lines", "tax_amount")
    op.drop_column("quotation_lines", "tax_rate")
    op.drop_index("ix_quotations_template_id", table_name="quotations")
    op.drop_constraint("fk_quotations_template_id", "quotations", type_="foreignkey")
    op.drop_column("quotations", "tax_total")
    op.drop_column("quotations", "payment_terms")
    op.drop_column("quotations", "validity_days")
    op.drop_column("quotations", "start_date")
    op.drop_column("quotations", "template_id")
    op.drop_index("ix_quotation_template_lines_template_id", table_name="quotation_template_lines")
    op.drop_table("quotation_template_lines")
    op.drop_index("ix_quotation_templates_created_by", table_name="quotation_templates")
    op.drop_index("ix_quotation_templates_active", table_name="quotation_templates")
    op.drop_table("quotation_templates")
