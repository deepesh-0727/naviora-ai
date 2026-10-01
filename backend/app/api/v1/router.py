from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    websocket,
    patients,
    appointments,
    queue,
    emergency,
    location,
    pharmacy,
    billing,
    analytics,
    doctors,
    navigation,
    notifications,
    admin,
    voice,
    feedback,
    staff,
)

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["authentication"])
api_router.include_router(websocket.router, tags=["websockets"])
api_router.include_router(patients.router, prefix="/patients", tags=["patients"])
api_router.include_router(appointments.router, prefix="/appointments", tags=["appointments"])
api_router.include_router(queue.router, prefix="/queue", tags=["queue"])
api_router.include_router(emergency.router, prefix="/emergency", tags=["emergency"])
api_router.include_router(location.router, prefix="/location", tags=["location"])
api_router.include_router(pharmacy.router, prefix="/pharmacy", tags=["pharmacy"])
api_router.include_router(billing.router, prefix="/billing", tags=["billing"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(doctors.router, prefix="/doctors", tags=["doctors"])
api_router.include_router(navigation.router, prefix="/navigation", tags=["navigation"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["notifications"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(voice.router, prefix="/voice", tags=["voice"])
api_router.include_router(feedback.router, prefix="/feedback", tags=["feedback"])
api_router.include_router(staff.router, prefix="/staff", tags=["staff"])