import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_emergency_trigger_requires_authentication(async_client: AsyncClient):
    response = await async_client.post("/api/v1/emergency/trigger", json={})
    assert response.status_code == 401
