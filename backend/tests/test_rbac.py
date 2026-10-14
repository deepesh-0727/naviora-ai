import pytest
from sqlalchemy import delete, select
from fastapi import HTTPException

from app.core.security import create_access_token
from app.core.rbac import require_permission
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
