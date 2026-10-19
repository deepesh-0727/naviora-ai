"""Reconcile runtime tables with the current SQLAlchemy models.

Revision ID: 5d88b0b6c31a
Revises: 4d7a92c61f30
"""
from typing import Sequence, Union

from alembic import op


revision: str = "5d88b0b6c31a"
down_revision: Union[str, None] = "4d7a92c61f30"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Each addition is nullable or has a server default so existing rows remain valid.
    statements = [
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS method VARCHAR(10)",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS duration_ms DOUBLE PRECISION",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS user_agent VARCHAR(255)",
        "ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS status VARCHAR(20) NOT NULL DEFAULT '200'",
        "ALTER TABLE appointments ADD COLUMN IF NOT EXISTS cancellation_reason TEXT",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS priority VARCHAR(20) NOT NULL DEFAULT 'normal'",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS read_at TIMESTAMP NULL",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS is_delivered BOOLEAN NOT NULL DEFAULT FALSE",
        "ALTER TABLE notifications ADD COLUMN IF NOT EXISTS delivered_at TIMESTAMP NULL",
        "ALTER TABLE billing ADD COLUMN IF NOT EXISTS payment_method VARCHAR(50)",
        "ALTER TABLE billing ADD COLUMN IF NOT EXISTS transaction_id VARCHAR(100)",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS audio_url VARCHAR(255)",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS duration DOUBLE PRECISION",
        "ALTER TABLE conversations ADD COLUMN IF NOT EXISTS sentiment VARCHAR(20)",
        "ALTER TABLE emergency_cases ADD COLUMN IF NOT EXISTS ambulance_id VARCHAR(50)",
        "ALTER TABLE emergency_cases ADD COLUMN IF NOT EXISTS response_time INTEGER",
        "ALTER TABLE emergency_cases ADD COLUMN IF NOT EXISTS acknowledged_at TIMESTAMP NULL",
        "ALTER TABLE emergency_cases ADD COLUMN IF NOT EXISTS en_route_at TIMESTAMP NULL",
        "ALTER TABLE emergency_cases ADD COLUMN IF NOT EXISTS treatment_notes TEXT",
        "ALTER TABLE emergency_cases ADD COLUMN IF NOT EXISTS assigned_staff JSON",
        "ALTER TABLE feedback ADD COLUMN IF NOT EXISTS categories JSON",
        "ALTER TABLE location_tracking ADD COLUMN IF NOT EXISTS accuracy DOUBLE PRECISION NOT NULL DEFAULT 1.0",
        "ALTER TABLE prescriptions ADD COLUMN IF NOT EXISTS instructions TEXT",
    ]
    for statement in statements:
        op.execute(statement)

    # Older production schemas used abbreviated vital names. Rename in place to
    # preserve any recorded data; add the expected column only if neither exists.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='patient_vitals' AND column_name='recorded_by')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='patient_vitals' AND column_name='recorded_by_id') THEN
                ALTER TABLE patient_vitals RENAME COLUMN recorded_by TO recorded_by_id;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='patient_vitals' AND column_name='bp_systolic')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='patient_vitals' AND column_name='blood_pressure_systolic') THEN
                ALTER TABLE patient_vitals RENAME COLUMN bp_systolic TO blood_pressure_systolic;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='patient_vitals' AND column_name='bp_diastolic')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='patient_vitals' AND column_name='blood_pressure_diastolic') THEN
                ALTER TABLE patient_vitals RENAME COLUMN bp_diastolic TO blood_pressure_diastolic;
            END IF;
        END $$;
    """)

    # The deployed schedule table used DATE + TIME columns. Convert those values
    # to the model's datetime representation without discarding the schedule.
    op.execute("""
        DO $$ BEGIN
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='staff_schedule' AND column_name='work_date')
               AND NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='staff_schedule' AND column_name='date') THEN
                ALTER TABLE staff_schedule ADD COLUMN date TIMESTAMP NULL;
                UPDATE staff_schedule SET date = work_date::timestamp;
                ALTER TABLE staff_schedule ALTER COLUMN date SET NOT NULL;
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='staff_schedule' AND column_name='start_time' AND data_type='time without time zone') THEN
                ALTER TABLE staff_schedule ALTER COLUMN start_time TYPE TIMESTAMP USING (work_date + start_time);
            END IF;
            IF EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema='public' AND table_name='staff_schedule' AND column_name='end_time' AND data_type='time without time zone') THEN
                ALTER TABLE staff_schedule ALTER COLUMN end_time TYPE TIMESTAMP USING (work_date + end_time);
            END IF;
        END $$;
    """)
    op.execute("ALTER TABLE staff_schedule ADD COLUMN IF NOT EXISTS shift_type VARCHAR(20) NOT NULL DEFAULT 'regular'")


def downgrade() -> None:
    # Keep this compatibility migration additive and data-safe on downgrade.
    # Removing columns or renaming deployed data back would cause data loss.
    pass
