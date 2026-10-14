"""
Naviora AI - Unified Model Registry
Aggregates all 15 clinical and operational database models.
"""

from .user import User
from .patient import Patient
from .doctor import Doctor, Department
from .appointment import Appointment
from .emergency import EmergencyCase
from .communication import Notification, ConversationHistory
from .hospital import AuditLog, Feedback, StaffSchedule
from .tracking import LocationTracking
from .vitals import PatientVitals
from .pharmacy import Prescription, Inventory
from .billing import Billing
from .security import RefreshToken
from .queue import QueueEntry
from .bed import Bed
from .operations import (
    Admission,
    BillingRefund,
    DepartmentWaypoint,
    Equipment,
    EmergencyMessage,
    LabOrder,
    MaintenanceRequest,
    MedicationAdministration,
    NurseHandover,
    OperatingRoom,
    OperatingRoomBooking,
    Referral,
    RegisteredDevice,
    StaffLeave,
    StaffAttendance,
    StaffShiftSwap,
    StaffSetting,
    SystemSetting,
)

__all__ = [
    "User",
    "Patient",
    "Doctor",
    "Department",
    "Appointment",
    "EmergencyCase",
    "Notification",
    "ConversationHistory",
    "AuditLog",
    "LocationTracking",
    "Feedback",
    "StaffSchedule",
    "PatientVitals",
    "Prescription",
    "Billing",
    "Inventory",
    "RefreshToken",
    "QueueEntry",
    "Bed",
    "LabOrder",
    "MaintenanceRequest",
    "MedicationAdministration",
    "NurseHandover",
    "Referral",
    "Admission",
    "BillingRefund",
    "Equipment",
    "EmergencyMessage",
    "OperatingRoom",
    "OperatingRoomBooking",
    "StaffLeave",
    "StaffAttendance",
    "StaffShiftSwap",
    "StaffSetting",
    "RegisteredDevice",
    "DepartmentWaypoint",
    "SystemSetting",
]
