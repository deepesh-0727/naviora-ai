"""Add persisted workflow and administration entities.

Revision ID: 5c73b9d14e2f
Revises: 92ac41d7b6e3
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "5c73b9d14e2f"
down_revision: Union[str, None] = "92ac41d7b6e3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "lab_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("ordered_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("test_name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(100), nullable=True),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("result", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_lab_orders_id", "lab_orders", ["id"])
    op.create_index("ix_lab_orders_patient_id", "lab_orders", ["patient_id"])
    op.create_index("ix_lab_orders_ordered_by_id", "lab_orders", ["ordered_by_id"])
    op.create_index("ix_lab_orders_status", "lab_orders", ["status"])

    op.create_table(
        "referrals",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("referring_doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=True),
        sa.Column("specialty", sa.String(120), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_referrals_id", "referrals", ["id"])
    op.create_index("ix_referrals_patient_id", "referrals", ["patient_id"])
    op.create_index("ix_referrals_status", "referrals", ["status"])

    op.create_table(
        "admissions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("patient_id", sa.Integer(), sa.ForeignKey("patients.id"), nullable=False),
        sa.Column("doctor_id", sa.Integer(), sa.ForeignKey("doctors.id"), nullable=False),
        sa.Column("bed_id", sa.Integer(), sa.ForeignKey("beds.id"), nullable=True),
        sa.Column("admitted_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="admitted"),
        sa.Column("admitted_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("discharged_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_admissions_id", "admissions", ["id"])
    op.create_index("ix_admissions_patient_id", "admissions", ["patient_id"])
    op.create_index("ix_admissions_status", "admissions", ["status"])

    op.create_table(
        "equipment",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("asset_tag", sa.String(80), nullable=False, unique=True),
        sa.Column("name", sa.String(160), nullable=False),
        sa.Column("category", sa.String(100), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="available"),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("last_maintenance", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_equipment_id", "equipment", ["id"])
    op.create_index("ix_equipment_asset_tag", "equipment", ["asset_tag"])
    op.create_index("ix_equipment_status", "equipment", ["status"])

    op.create_table(
        "maintenance_requests",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("location", sa.String(160), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="open"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_maintenance_requests_id", "maintenance_requests", ["id"])
    op.create_index("ix_maintenance_requests_requested_by_id", "maintenance_requests", ["requested_by_id"])
    op.create_index("ix_maintenance_requests_status", "maintenance_requests", ["status"])

    op.create_table(
        "operating_rooms",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("room_number", sa.String(50), nullable=False, unique=True),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="available"),
        sa.Column("status_reason", sa.Text(), nullable=True),
    )
    op.create_index("ix_operating_rooms_id", "operating_rooms", ["id"])
    op.create_index("ix_operating_rooms_room_number", "operating_rooms", ["room_number"])
    op.create_index("ix_operating_rooms_status", "operating_rooms", ["status"])

    op.create_table(
        "operating_room_bookings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("operating_room_id", sa.Integer(), sa.ForeignKey("operating_rooms.id"), nullable=False),
        sa.Column("appointment_id", sa.Integer(), sa.ForeignKey("appointments.id"), nullable=True),
        sa.Column("requested_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("procedure", sa.String(180), nullable=False),
        sa.Column("scheduled_start", sa.DateTime(), nullable=False),
        sa.Column("scheduled_end", sa.DateTime(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="scheduled"),
    )
    op.create_index("ix_operating_room_bookings_id", "operating_room_bookings", ["id"])
    op.create_index("ix_operating_room_bookings_operating_room_id", "operating_room_bookings", ["operating_room_id"])
    op.create_index("ix_operating_room_bookings_scheduled_start", "operating_room_bookings", ["scheduled_start"])
    op.create_index("ix_operating_room_bookings_status", "operating_room_bookings", ["status"])

    op.create_table(
        "staff_leaves",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("staff_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_staff_leaves_id", "staff_leaves", ["id"])
    op.create_index("ix_staff_leaves_staff_id", "staff_leaves", ["staff_id"])
    op.create_index("ix_staff_leaves_status", "staff_leaves", ["status"])

    op.create_table(
        "staff_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", name="uq_staff_settings_user_id"),
    )
    op.create_index("ix_staff_settings_id", "staff_settings", ["id"])
    op.create_index("ix_staff_settings_user_id", "staff_settings", ["user_id"])

    op.create_table(
        "registered_devices",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("platform", sa.String(30), nullable=False),
        sa.Column("token_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("last_seen", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_registered_devices_id", "registered_devices", ["id"])
    op.create_index("ix_registered_devices_user_id", "registered_devices", ["user_id"])
    op.create_index("ix_registered_devices_token_hash", "registered_devices", ["token_hash"])

    op.create_table(
        "department_waypoints",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("department_id", sa.Integer(), sa.ForeignKey("departments.id"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("floor", sa.Integer(), nullable=False),
        sa.Column("building", sa.String(80), nullable=False),
        sa.Column("x_coordinate", sa.Float(), nullable=False),
        sa.Column("y_coordinate", sa.Float(), nullable=False),
        sa.Column("connected_to_id", sa.Integer(), sa.ForeignKey("department_waypoints.id"), nullable=True),
    )
    op.create_index("ix_department_waypoints_id", "department_waypoints", ["id"])
    op.create_index("ix_department_waypoints_department_id", "department_waypoints", ["department_id"])

    op.create_table(
        "system_settings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("key", sa.String(120), nullable=False, unique=True),
        sa.Column("value", sa.JSON(), nullable=False),
        sa.Column("updated_by_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_system_settings_id", "system_settings", ["id"])
    op.create_index("ix_system_settings_key", "system_settings", ["key"])


def downgrade() -> None:
    op.drop_table("system_settings")
    op.drop_table("department_waypoints")
    op.drop_table("registered_devices")
    op.drop_table("staff_settings")
    op.drop_table("staff_leaves")
    op.drop_table("operating_room_bookings")
    op.drop_table("operating_rooms")
    op.drop_table("equipment")
    op.drop_table("maintenance_requests")
    op.drop_table("admissions")
    op.drop_table("referrals")
    op.drop_table("lab_orders")
