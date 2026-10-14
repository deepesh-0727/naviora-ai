"""Add persistent staff attendance and shift swap records.

Revision ID: e639af48c927
Revises: ad12f111e22c
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e639af48c927"
down_revision: Union[str, None] = "ad12f111e22c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "staff_shift_swaps",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("staff_schedule.id"), nullable=True),
        sa.Column("request_details", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_staff_shift_swaps_id", "staff_shift_swaps", ["id"])
    op.create_index("ix_staff_shift_swaps_staff_id", "staff_shift_swaps", ["staff_id"])
    op.create_index("ix_staff_shift_swaps_status", "staff_shift_swaps", ["status"])

    op.create_table(
        "staff_attendance",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("schedule_id", sa.Integer(), sa.ForeignKey("staff_schedule.id"), nullable=True),
        sa.Column("checked_in_at", sa.DateTime(), nullable=True),
        sa.Column("checked_out_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_staff_attendance_id", "staff_attendance", ["id"])
    op.create_index("ix_staff_attendance_staff_id", "staff_attendance", ["staff_id"])
    op.create_index("ix_staff_attendance_status", "staff_attendance", ["status"])


def downgrade() -> None:
    op.drop_table("staff_attendance")
    op.drop_table("staff_shift_swaps")
