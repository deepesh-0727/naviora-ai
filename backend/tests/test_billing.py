import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_billing_endpoints_require_authentication(async_client: AsyncClient):
    response = await async_client.get("/api/v1/billing/invoices")
    assert response.status_code == 401
