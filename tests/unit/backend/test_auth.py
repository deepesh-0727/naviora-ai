import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from app.core import security
from app.models.user import User

@pytest.mark.asyncio
async def test_register_patient(client: AsyncClient):
    payload = {
        "phone": "+919876543210",
        "email": "test@naviora.ai",
        "password": "testpassword123",
        "first_name": "Test",
        "last_name": "Patient",
        "date_of_birth": "1990-01-01",
        "gender": "male",
        "emergency_contact": "+919876543211",
        "emergency_contact_name": "Emergency Contact"
    }
    response = await client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    assert response.json()["phone"] == "+919876543210"

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    # Setup: Create a user
    hashed_pw = security.get_password_hash("testpassword123")
    user = User(
        phone="+919999988888",
        email="login_test@naviora.ai",
        password_hash=hashed_pw,
        is_active=True,
        is_verified=True,
        role="patient"
    )
    db_session.add(user)
    await db_session.commit()

    # Test login
    login_data = {
        "username": "+919999988888",
        "password": "testpassword123"
    }
    response = await client.post(
        "/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"

@pytest.mark.asyncio
async def test_login_invalid_password(client: AsyncClient):
    login_data = {
        "username": "+919999988888",
        "password": "wrongpassword"
    }
    response = await client.post(
        "/api/v1/auth/login",
        data=login_data,
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    assert response.status_code == 400
    assert "Incorrect phone number or password" in response.json()["detail"]
