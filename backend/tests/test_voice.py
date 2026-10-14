import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_voice_processing_requires_authentication(async_client: AsyncClient):
    response = await async_client.post("/api/v1/voice/process")
    assert response.status_code == 401
