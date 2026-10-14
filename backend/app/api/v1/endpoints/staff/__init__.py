from fastapi import APIRouter

from app.api.v1.endpoints.staff import (
    doctor,
    emergency,
    facilities,
    frontdesk,
    notifications,
    nurse,
    patients,
    pharmacy,
    prescriptions,
    profile,
    queue,
    settings,
)
from app.api.v1.endpoints.staff.profile_base import router as base_profile_router

router = APIRouter()
router.include_router(base_profile_router)
router.include_router(doctor.router, prefix="/doctor", tags=["staff-doctor"])
router.include_router(queue.router, prefix="/queue", tags=["staff-queue"])
router.include_router(nurse.router, prefix="/nurse", tags=["staff-nurse"])
router.include_router(frontdesk.router, tags=["staff-front-desk"])
router.include_router(pharmacy.router, prefix="/pharmacy", tags=["staff-pharmacy"])
router.include_router(facilities.router, prefix="/facilities", tags=["staff-facilities"])
router.include_router(emergency.router, prefix="/emergency", tags=["staff-emergency"])
router.include_router(patients.router, prefix="/patients", tags=["staff-patients"])
router.include_router(prescriptions.router, tags=["staff-orders"])
router.include_router(notifications.router, prefix="/notifications", tags=["staff-notifications"])
router.include_router(profile.router)
router.include_router(settings.router)
