"""Add persisted billing refund requests.

Revision ID: f295a7e4c811
Revises: e639af48c927
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f295a7e4c811"
down_revision: Union[str, None] = "e639af48c927"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "billing_refunds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("billing_id", sa.Integer(), sa.ForeignKey("billing.id"), nullable=False),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_billing_refunds_id", "billing_refunds", ["id"])
    op.create_index("ix_billing_refunds_billing_id", "billing_refunds", ["billing_id"])
    op.create_index("ix_billing_refunds_status", "billing_refunds", ["status"])


def downgrade() -> None:
    op.drop_table("billing_refunds")
