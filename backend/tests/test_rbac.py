import pytest
from sqlalchemy import delete, select
from fastapi import HTTPException

from app.core.security import create_access_token
from app.core.rbac import ROLE_PERMISSIONS, require_permission
from app.models.hospital import AuditLog
from app.models.user import User


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("role", "path"),
    [
        ("patient", "/api/v1/staff/profile"),
        ("nurse", "/api/v1/admin/dashboard/kpis"),
    ],
)
async def test_cross_role_api_access_is_rejected(async_client, db_session, role, path):
    user = User(
        phone=f"+9198000000{100 + len(role)}",
        email=f"{role}@rbac.test",
        password_hash="stored-password-hash",
        role=role,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    token = create_access_token(subject=user.id, claims={"role": role})

    response = await async_client.get(path, headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403
    audit_result = await db_session.execute(
        select(AuditLog).where(
            AuditLog.user_id == user.id,
            AuditLog.method == "GET",
            AuditLog.resource_id == path,
        )
    )
    assert audit_result.scalar_one_or_none() is not None
    await db_session.execute(delete(User).where(User.id == user.id))
    await db_session.commit()


def test_permission_dependencies_apply_the_role_matrix():
    patient = User(role="patient")
    nurse = User(role="nurse")

    assert require_permission("view_own_profile")(patient) is patient
    assert require_permission("view_patient")(nurse) is nurse
    with pytest.raises(HTTPException) as denied:
        require_permission("view_patient")(patient)
    assert denied.value.status_code == 403


@pytest.mark.parametrize(
    ("role", "allowed_permission", "denied_permission"),
    [
        ("patient", "manage_own_appointments", "manage_queue"),
        ("doctor", "manage_queue", "manage_departments"),
        ("nurse", "record_vitals", "manage_system"),
        ("front_desk", "register_walk_in", "view_audit"),
        ("pharmacy", "dispense_medications", "manage_maintenance"),
        ("facilities", "manage_beds", "manage_staff"),
        ("emergency", "manage_emergency", "manage_appointments"),
        ("staff", "view_patient", "manage_system"),
        ("admin", "view_audit", "manage_system"),
        ("super_admin", "manage_system", "trigger_emergency"),
    ],
)
def test_role_permission_matrix_allows_own_capabilities_and_denies_cross_role(role, allowed_permission, denied_permission):
    user = User(role=role)

    assert allowed_permission in ROLE_PERMISSIONS[role]
    assert require_permission(allowed_permission)(user) is user
    assert denied_permission not in ROLE_PERMISSIONS[role]
    with pytest.raises(HTTPException) as denied:
        require_permission(denied_permission)(user)
    assert denied.value.status_code == 403
