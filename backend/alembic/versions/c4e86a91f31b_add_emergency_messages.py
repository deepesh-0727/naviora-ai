"""Persist staff emergency conversation messages.

Revision ID: c4e86a91f31b
Revises: bd15f8c2a010
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4e86a91f31b"
down_revision: Union[str, None] = "bd15f8c2a010"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "emergency_messages",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("emergency_id", sa.Integer(), sa.ForeignKey("emergency_cases.id"), nullable=False),
        sa.Column("sender_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_emergency_messages_id", "emergency_messages", ["id"])
    op.create_index("ix_emergency_messages_emergency_id", "emergency_messages", ["emergency_id"])
    op.create_index("ix_emergency_messages_sender_id", "emergency_messages", ["sender_id"])


def downgrade() -> None:
    op.drop_table("emergency_messages")
