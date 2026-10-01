"""Add persisted patient vitals.

Revision ID: 92ac41d7b6e3
Revises: 3064f88fee99
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "92ac41d7b6e3"
down_revision: Union[str, None] = "3064f88fee99"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "patient_vitals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("recorded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("blood_pressure_systolic", sa.Integer(), nullable=False),
        sa.Column("blood_pressure_diastolic", sa.Integer(), nullable=False),
        sa.Column("heart_rate", sa.Integer(), nullable=False),
        sa.Column("temperature", sa.Float(), nullable=False),
        sa.Column("spo2", sa.Integer(), nullable=False),
        sa.Column("weight", sa.Float(), nullable=True),
        sa.Column("height", sa.Float(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("recorded_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_patient_vitals_id", "patient_vitals", ["id"])
    op.create_index("ix_patient_vitals_patient_id", "patient_vitals", ["patient_id"])
    op.create_index("ix_patient_vitals_recorded_at", "patient_vitals", ["recorded_at"])


def downgrade() -> None:
    op.drop_index("ix_patient_vitals_recorded_at", table_name="patient_vitals")
    op.drop_index("ix_patient_vitals_patient_id", table_name="patient_vitals")
    op.drop_index("ix_patient_vitals_id", table_name="patient_vitals")
    op.drop_table("patient_vitals")
