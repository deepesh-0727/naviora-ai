"""Encrypt patient PII with the configured Fernet key.

Revision ID: 4c2d9b8e1a70
Revises: 92ac41d7b6e3
"""
import json
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from cryptography.fernet import Fernet

from app.core.config import settings

revision: str = "4c2d9b8e1a70"
down_revision: Union[str, None] = "92ac41d7b6e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


PII_FIELDS = (
    "first_name",
    "last_name",
    "allergies",
    "emergency_contact",
    "emergency_contact_name",
    "medical_history",
)


def _cipher() -> Fernet:
    key = settings.ENCRYPTION_KEY.strip()
    if not key:
        raise RuntimeError("Set ENCRYPTION_KEY before applying the patient PII migration.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("ENCRYPTION_KEY must be a valid Fernet key.") from exc


def upgrade() -> None:
    cipher = _cipher()
    bind = op.get_bind()

    op.add_column("audit_logs", sa.Column("method", sa.String(length=10), nullable=True))
    op.add_column("audit_logs", sa.Column("duration_ms", sa.Float(), nullable=True))
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_id", "refresh_tokens", ["id"])
    op.create_index("ix_refresh_tokens_user_id", "refresh_tokens", ["user_id"])
    op.create_index("ix_refresh_tokens_token_hash", "refresh_tokens", ["token_hash"], unique=True)
    op.create_table(
        "queue_entries",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="queued"),
        sa.Column("entered_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("served_at", sa.DateTime(), nullable=True),
        sa.UniqueConstraint("appointment_id", name="uq_queue_entries_appointment"),
    )
    op.create_index("ix_queue_entries_id", "queue_entries", ["id"])
    op.create_index("ix_queue_entries_doctor_id", "queue_entries", ["doctor_id"])
    op.create_table(
        "beds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("ward", sa.String(length=100), nullable=False),
        sa.Column("bed_number", sa.String(length=40), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="available"),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("ward", "bed_number", name="uq_beds_ward_bed_number"),
    )
    op.create_index("ix_beds_id", "beds", ["id"])
    op.create_index("ix_beds_ward", "beds", ["ward"])
    op.create_index("ix_beds_patient_id", "beds", ["patient_id"])

    for name, length in (
        ("first_name", 50),
        ("last_name", 50),
        ("emergency_contact", 20),
        ("emergency_contact_name", 100),
    ):
        op.alter_column(
            "patients",
            name,
            existing_type=sa.String(length),
            type_=sa.Text(),
            existing_nullable=False,
            postgresql_using=f"{name}::text",
        )
    op.alter_column(
        "patients",
        "allergies",
        existing_type=sa.JSON(),
        type_=sa.Text(),
        existing_nullable=True,
        postgresql_using="allergies::text",
    )

    rows = bind.execute(
        sa.text("SELECT id, first_name, last_name, allergies, emergency_contact, emergency_contact_name, medical_history FROM patients")
    ).mappings()
    update = sa.text(
        "UPDATE patients SET first_name=:first_name, last_name=:last_name, allergies=:allergies, "
        "emergency_contact=:emergency_contact, emergency_contact_name=:emergency_contact_name, "
        "medical_history=:medical_history WHERE id=:id"
    )
    for row in rows:
        values: dict[str, object] = {"id": row["id"]}
        for field in PII_FIELDS:
            value = row[field]
            if field == "allergies" and value is not None:
                if isinstance(value, str):
                    value = json.loads(value)
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            if value is not None:
                value = cipher.encrypt(str(value).encode("utf-8")).decode("ascii")
            values[field] = value
        bind.execute(update, values)


def downgrade() -> None:
    cipher = _cipher()
    bind = op.get_bind()
    rows = bind.execute(
        sa.text("SELECT id, first_name, last_name, allergies, emergency_contact, emergency_contact_name, medical_history FROM patients")
    ).mappings()
    update = sa.text(
        "UPDATE patients SET first_name=:first_name, last_name=:last_name, allergies=:allergies, "
        "emergency_contact=:emergency_contact, emergency_contact_name=:emergency_contact_name, "
        "medical_history=:medical_history WHERE id=:id"
    )
    for row in rows:
        values: dict[str, object] = {"id": row["id"]}
        for field in PII_FIELDS:
            value = row[field]
            if value is not None:
                value = cipher.decrypt(str(value).encode("ascii")).decode("utf-8")
            if field == "allergies" and value is not None:
                value = json.dumps(json.loads(value), ensure_ascii=False, separators=(",", ":"))
            values[field] = value
        bind.execute(update, values)

    op.alter_column(
        "patients", "first_name", existing_type=sa.Text(), type_=sa.String(50),
        existing_nullable=False, postgresql_using="first_name::varchar(50)",
    )
    op.alter_column(
        "patients", "last_name", existing_type=sa.Text(), type_=sa.String(50),
        existing_nullable=False, postgresql_using="last_name::varchar(50)",
    )
    op.alter_column(
        "patients", "emergency_contact", existing_type=sa.Text(), type_=sa.String(20),
        existing_nullable=False, postgresql_using="emergency_contact::varchar(20)",
    )
    op.alter_column(
        "patients", "emergency_contact_name", existing_type=sa.Text(), type_=sa.String(100),
        existing_nullable=False, postgresql_using="emergency_contact_name::varchar(100)",
    )
    op.alter_column(
        "patients", "allergies", existing_type=sa.Text(), type_=sa.JSON(),
        existing_nullable=True, postgresql_using="allergies::json",
    )
    op.drop_column("audit_logs", "duration_ms")
    op.drop_column("audit_logs", "method")
    op.drop_index("ix_beds_patient_id", table_name="beds")
    op.drop_index("ix_beds_ward", table_name="beds")
    op.drop_index("ix_beds_id", table_name="beds")
    op.drop_table("beds")
    op.drop_index("ix_queue_entries_doctor_id", table_name="queue_entries")
    op.drop_index("ix_queue_entries_id", table_name="queue_entries")
    op.drop_table("queue_entries")
    op.drop_index("ix_refresh_tokens_token_hash", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_user_id", table_name="refresh_tokens")
    op.drop_index("ix_refresh_tokens_id", table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
