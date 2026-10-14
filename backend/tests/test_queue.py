import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_queue_status_requires_authentication(async_client: AsyncClient):
    response = await async_client.get("/api/v1/queue/status/1")
    assert response.status_code == 401
