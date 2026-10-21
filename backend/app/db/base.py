# Import all the models, so that Base has them before being
# imported by Alembic or used for migrations.
from app.db.base_class import Base  # noqa

# Import all models to register them on the Base metadata
from app.models.user import User  # noqa
from app.models.patient import Patient  # noqa
from app.models.doctor import Doctor, Department  # noqa
from app.models.nurse import NurseProfile  # noqa
from app.models.appointment import Appointment  # noqa
from app.models.emergency import EmergencyCase  # noqa
from app.models.communication import Notification, ConversationHistory  # noqa
from app.models.hospital import AuditLog, Feedback, StaffSchedule  # noqa
from app.models.tracking import LocationTracking  # noqa
from app.models.pharmacy import Prescription, Inventory  # noqa
from app.models.billing import Billing  # noqa
from app.models.vitals import PatientVitals  # noqa
from app.models.security import RefreshToken  # noqa
from app.models.queue import QueueEntry  # noqa
from app.models.voice_interaction import VoiceInteraction  # noqa
from app.models.feedback_reminder import FeedbackReminder  # noqa
from app.models.bed import Bed  # noqa
from app.models.operations import (  # noqa
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
