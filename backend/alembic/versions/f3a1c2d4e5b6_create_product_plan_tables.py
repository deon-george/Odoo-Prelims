"""create product and subscription plan tables

Revision ID: f3a1c2d4e5b6
Revises: eb5386a0fc02
Create Date: 2026-10-31 12:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "f3a1c2d4e5b6"
down_revision: Union[str, None] = "eb5386a0fc02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TABLE_KWARGS = {
    "mysql_engine": "InnoDB",
    "mysql_charset": "utf8mb4",
    "mysql_collate": "utf8mb4_0900_ai_ci",
}


def upgrade() -> None:
    op.create_table(
        "products",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("product_type", sa.String(length=50), nullable=True),
        sa.Column("base_price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text(
                "CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "`status` IN ('active', 'inactive')",
            name="ck_products_status",
        ),
        sa.CheckConstraint("base_price >= 0", name="ck_products_base_price"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name", name="uq_products_name"),
        **TABLE_KWARGS,
    )
    op.create_index("ix_products_status", "products", ["status"], unique=False)

    op.create_table(
        "subscription_plans",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("product_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column("billing_interval", sa.String(length=20), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default="active",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text("CURRENT_TIMESTAMP(6)"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            mysql.DATETIME(fsp=6),
            server_default=sa.text(
                "CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6)"
            ),
            nullable=False,
        ),
        sa.CheckConstraint(
            "`billing_interval` IN ('monthly', 'quarterly', 'yearly')",
            name="ck_subscription_plans_billing_interval",
        ),
        sa.CheckConstraint("price >= 0", name="ck_subscription_plans_price"),
        sa.CheckConstraint(
            "`status` IN ('active', 'inactive')",
            name="ck_subscription_plans_status",
        ),
        sa.ForeignKeyConstraint(
            ["product_id"],
            ["products.id"],
            name="fk_subscription_plans_product_id",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "name",
            "billing_interval",
            name="uq_subscription_plans_product_name_interval",
        ),
        **TABLE_KWARGS,
    )
    op.create_index(
        "ix_subscription_plans_product_id",
        "subscription_plans",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_plans_status",
        "subscription_plans",
        ["status"],
        unique=False,
    )
    op.create_index(
        "ix_subscription_plans_billing_interval",
        "subscription_plans",
        ["billing_interval"],
        unique=False,
    )

    op.create_table(
        "plan_features",
        sa.Column(
            "id",
            mysql.BIGINT(unsigned=True),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("plan_id", mysql.BIGINT(unsigned=True), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column(
            "sort_order",
            mysql.INTEGER(unsigned=True),
            server_default="0",
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["plan_id"],
            ["subscription_plans.id"],
            name="fk_plan_features_plan_id",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "plan_id",
            "label",
            name="uq_plan_features_plan_label",
        ),
        **TABLE_KWARGS,
    )
    op.create_index(
        "ix_plan_features_plan_id",
        "plan_features",
        ["plan_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_plan_features_plan_id", table_name="plan_features")
    op.drop_table("plan_features")

    op.drop_index(
        "ix_subscription_plans_billing_interval",
        table_name="subscription_plans",
    )
    op.drop_index(
        "ix_subscription_plans_status",
        table_name="subscription_plans",
    )
    op.drop_index(
        "ix_subscription_plans_product_id",
        table_name="subscription_plans",
    )
    op.drop_table("subscription_plans")

    op.drop_index("ix_products_status", table_name="products")
    op.drop_table("products")
