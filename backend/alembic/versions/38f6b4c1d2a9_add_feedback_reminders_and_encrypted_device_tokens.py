"""Add durable feedback reminders and encrypted push tokens.

Revision ID: 38f6b4c1d2a9
Revises: 1b2193d76fcc
"""
from typing import Sequence, Union

from alembic import op


revision: str = "38f6b4c1d2a9"
down_revision: Union[str, None] = "1b2193d76fcc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Some deployments provisioned these objects manually before this revision
    # was recorded. Keep the migration safe for both those databases and fresh ones.
    op.execute("ALTER TABLE registered_devices ADD COLUMN IF NOT EXISTS token_encrypted TEXT")
    op.execute("""
        CREATE TABLE IF NOT EXISTS feedback_reminders (
            id SERIAL PRIMARY KEY,
            appointment_id INTEGER NOT NULL REFERENCES appointments(id),
            patient_id INTEGER NOT NULL REFERENCES patients(id),
            scheduled_at TIMESTAMP NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            processing_at TIMESTAMP NULL,
            attempts INTEGER NOT NULL DEFAULT 0,
            sent_at TIMESTAMP NULL,
            last_error VARCHAR(500) NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT uq_feedback_reminders_appointment_id UNIQUE (appointment_id)
        )
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_reminders_appointment_id ON feedback_reminders (appointment_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_reminders_patient_id ON feedback_reminders (patient_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_reminders_scheduled_at ON feedback_reminders (scheduled_at)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_feedback_reminders_status ON feedback_reminders (status)")


def downgrade() -> None:
    op.drop_table("feedback_reminders")
    op.drop_column("registered_devices", "token_encrypted")
