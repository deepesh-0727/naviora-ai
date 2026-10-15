import pytest


@pytest.mark.asyncio
async def test_rbac_journey_denies_patient_staff_and_admin_cross_role_access(async_client, hospital_actors):
    cases = [
        ("patient", "/api/v1/staff/profile"),
        ("doctor", "/api/v1/admin/dashboard/kpis"),
        ("admin", "/api/v1/patients/profile"),
    ]

    for role, path in cases:
        response = await async_client.get(
            path,
            headers={"Authorization": f"Bearer {hospital_actors['tokens'][role]}"},
        )
        assert response.status_code == 403
        assert "detail" in response.json()
