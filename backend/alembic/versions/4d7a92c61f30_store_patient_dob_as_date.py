"""store patient date of birth as a date

Revision ID: 4d7a92c61f30
Revises: 38f6b4c1d2a9
Create Date: 2026-10-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "4d7a92c61f30"
down_revision: Union[str, None] = "38f6b4c1d2a9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "patients",
        "date_of_birth",
        existing_type=sa.DateTime(),
        type_=sa.Date(),
        postgresql_using="date_of_birth::date",
    )


def downgrade() -> None:
    op.alter_column(
        "patients",
        "date_of_birth",
        existing_type=sa.Date(),
        type_=sa.DateTime(),
        postgresql_using="date_of_birth::timestamp",
    )
