from fastapi import APIRouter

from app.api.v1.endpoints.admin import (
    analytics,
    audit,
    billing,
    dashboard,
    departments,
    health,
    pilot_metrics,
    resources,
    settings,
    staff,
    users,
)

router = APIRouter()
router.include_router(dashboard.router, prefix="/dashboard", tags=["admin-dashboard"])
router.include_router(users.router, prefix="/users", tags=["admin-users"])
router.include_router(staff.router, prefix="/staff", tags=["admin-staff"])
router.include_router(departments.router, prefix="/departments", tags=["admin-departments"])
router.include_router(resources.router, prefix="/resources", tags=["admin-resources"])
router.include_router(analytics.router, prefix="/analytics", tags=["admin-analytics"])
router.include_router(audit.router, prefix="/audit", tags=["admin-audit"])
router.include_router(billing.router, prefix="/billing", tags=["admin-billing"])
router.include_router(health.router, prefix="/health", tags=["admin-health"])
router.include_router(pilot_metrics.router, prefix="/pilot", tags=["admin-pilot"])
router.include_router(settings.router, prefix="/settings", tags=["admin-settings"])
