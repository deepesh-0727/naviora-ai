"""Persist emergency timeline milestones.

Revision ID: ad12f111e22c
Revises: c4e86a91f31b
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "ad12f111e22c"
down_revision: Union[str, None] = "c4e86a91f31b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("emergency_cases", sa.Column("acknowledged_at", sa.DateTime(), nullable=True))
    op.add_column("emergency_cases", sa.Column("en_route_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    op.drop_column("emergency_cases", "en_route_at")
    op.drop_column("emergency_cases", "acknowledged_at")
