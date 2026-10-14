"""Add persistent medication administration and handover records.

Revision ID: bd15f8c2a010
Revises: 5c73b9d14e2f
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "bd15f8c2a010"
down_revision: Union[str, None] = "5c73b9d14e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "medication_administrations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("prescription_id", sa.Integer(), sa.ForeignKey("prescriptions.id"), nullable=True),
        sa.Column("recorded_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("medication", sa.String(160), nullable=False),
        sa.Column("due_at", sa.DateTime(), nullable=False),
        sa.Column("administered_at", sa.DateTime(), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="due"),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_medication_administrations_id", "medication_administrations", ["id"])
    op.create_index("ix_medication_administrations_patient_id", "medication_administrations", ["patient_id"])
    op.create_index("ix_medication_administrations_due_at", "medication_administrations", ["due_at"])
    op.create_index("ix_medication_administrations_status", "medication_administrations", ["status"])

    op.create_table(
        "nurse_handovers",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("nurse_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("ward", sa.String(100), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_nurse_handovers_id", "nurse_handovers", ["id"])
    op.create_index("ix_nurse_handovers_nurse_id", "nurse_handovers", ["nurse_id"])
    op.create_index("ix_nurse_handovers_ward", "nurse_handovers", ["ward"])


def downgrade() -> None:
    op.drop_table("nurse_handovers")
    op.drop_table("medication_administrations")
