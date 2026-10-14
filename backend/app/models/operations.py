import datetime
from decimal import Decimal

from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class LabOrder(Base):
    __tablename__ = "lab_orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    ordered_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    test_name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())
    completed_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class Referral(Base):
    __tablename__ = "referrals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    referring_doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    department_id: Mapped[int | None] = mapped_column(ForeignKey("departments.id"), nullable=True)
    specialty: Mapped[str] = mapped_column(String(120), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class Admission(Base):
    __tablename__ = "admissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    doctor_id: Mapped[int] = mapped_column(ForeignKey("doctors.id"))
    bed_id: Mapped[int | None] = mapped_column(ForeignKey("beds.id"), nullable=True)
    admitted_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="admitted", server_default="admitted", index=True)
    admitted_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())
    discharged_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class Equipment(Base):
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    asset_tag: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="available", server_default="available", index=True)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    last_maintenance: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)


class MaintenanceRequest(Base):
    __tablename__ = "maintenance_requests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    location: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="open", server_default="open", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class OperatingRoom(Base):
    __tablename__ = "operating_rooms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    room_number: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="available", server_default="available", index=True)
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)


class OperatingRoomBooking(Base):
    __tablename__ = "operating_room_bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    operating_room_id: Mapped[int] = mapped_column(ForeignKey("operating_rooms.id"), index=True)
    appointment_id: Mapped[int | None] = mapped_column(ForeignKey("appointments.id"), nullable=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    procedure: Mapped[str] = mapped_column(String(180), nullable=False)
    scheduled_start: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    scheduled_end: Mapped[datetime.datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", server_default="scheduled", index=True)


class StaffLeave(Base):
    __tablename__ = "staff_leaves"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    starts_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    ends_on: Mapped[datetime.date] = mapped_column(Date, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class StaffShiftSwap(Base):
    __tablename__ = "staff_shift_swaps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("staff_schedule.id"), nullable=True)
    request_details: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class StaffAttendance(Base):
    __tablename__ = "staff_attendance"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    staff_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    schedule_id: Mapped[int | None] = mapped_column(ForeignKey("staff_schedule.id"), nullable=True)
    checked_in_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    checked_out_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="scheduled", server_default="scheduled", index=True)
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class MedicationAdministration(Base):
    __tablename__ = "medication_administrations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), index=True)
    prescription_id: Mapped[int | None] = mapped_column(ForeignKey("prescriptions.id"), nullable=True)
    recorded_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    medication: Mapped[str] = mapped_column(String(160), nullable=False)
    due_at: Mapped[datetime.datetime] = mapped_column(DateTime, index=True)
    administered_at: Mapped[datetime.datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="due", server_default="due", index=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class NurseHandover(Base):
    __tablename__ = "nurse_handovers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    nurse_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    ward: Mapped[str] = mapped_column(String(100), index=True)
    notes: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class EmergencyMessage(Base):
    __tablename__ = "emergency_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    emergency_id: Mapped[int] = mapped_column(ForeignKey("emergency_cases.id"), index=True)
    sender_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class StaffSetting(Base):
    __tablename__ = "staff_settings"
    __table_args__ = (UniqueConstraint("user_id", name="uq_staff_settings_user_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    preferences: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, server_default=func.now())


class RegisteredDevice(Base):
    __tablename__ = "registered_devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    platform: Mapped[str] = mapped_column(String(30), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    last_seen: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())


class DepartmentWaypoint(Base):
    __tablename__ = "department_waypoints"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(ForeignKey("departments.id"), index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    floor: Mapped[int] = mapped_column(Integer, nullable=False)
    building: Mapped[str] = mapped_column(String(80), nullable=False)
    x_coordinate: Mapped[float] = mapped_column(Float, nullable=False)
    y_coordinate: Mapped[float] = mapped_column(Float, nullable=False)
    connected_to_id: Mapped[int | None] = mapped_column(ForeignKey("department_waypoints.id"), nullable=True)


class SystemSetting(Base):
    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    key: Mapped[str] = mapped_column(String(120), unique=True, index=True)
    value: Mapped[dict] = mapped_column(JSON, nullable=False)
    updated_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    updated_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow, server_default=func.now())


class BillingRefund(Base):
    __tablename__ = "billing_refunds"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    billing_id: Mapped[int] = mapped_column(ForeignKey("billing.id"), index=True)
    requested_by_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="pending", server_default="pending", index=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime, default=datetime.datetime.utcnow, server_default=func.now())
