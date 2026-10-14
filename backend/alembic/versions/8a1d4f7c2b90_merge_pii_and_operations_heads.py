"""Merge patient PII encryption and operational schema migration heads.

Revision ID: 8a1d4f7c2b90
Revises: 4c2d9b8e1a70, f295a7e4c811
"""
from typing import Sequence, Union


revision: str = "8a1d4f7c2b90"
down_revision: Union[str, Sequence[str], None] = ("4c2d9b8e1a70", "f295a7e4c811")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
