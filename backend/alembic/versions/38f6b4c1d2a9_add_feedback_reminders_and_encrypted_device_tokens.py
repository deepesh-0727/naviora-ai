"""Add durable feedback reminders and encrypted push tokens.

Revision ID: 38f6b4c1d2a9
Revises: 1b2193d76fcc
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "38f6b4c1d2a9"
down_revision: Union[str, None] = "1b2193d76fcc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("registered_devices", sa.Column("token_encrypted", sa.Text(), nullable=True))
    op.create_table(
        "feedback_reminders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("scheduled_at", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("processing_at", sa.DateTime(), nullable=True),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.String(500), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("appointment_id", name="uq_feedback_reminders_appointment_id"),
    )
    op.create_index("ix_feedback_reminders_appointment_id", "feedback_reminders", ["appointment_id"])
    op.create_index("ix_feedback_reminders_patient_id", "feedback_reminders", ["patient_id"])
    op.create_index("ix_feedback_reminders_scheduled_at", "feedback_reminders", ["scheduled_at"])
    op.create_index("ix_feedback_reminders_status", "feedback_reminders", ["status"])


def downgrade() -> None:
    op.drop_table("feedback_reminders")
    op.drop_column("registered_devices", "token_encrypted")
