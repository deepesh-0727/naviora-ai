import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_placeholder(async_client: AsyncClient):
    assert True
