from datetime import datetime, timedelta, timezone
import hashlib

import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.security import create_access_token, create_refresh_token, get_password_hash
from app.models.patient import Patient
from app.models.security import RefreshToken
from app.models.user import User


@pytest.fixture
async def auth_api_context(db_session, monkeypatch):
    from app.api.v1.endpoints import auth as auth_module

    monkeypatch.setattr(auth_module.limiter, "enabled", False, raising=False)
    user = User(
        phone="9800007701", email="auth.coverage@tests.example", password_hash=get_password_hash("Correct-password-123!"),
        role="patient", is_active=True, is_verified=True,
    )
    duplicate_email_user = User(
        phone="9800007702", email="duplicate.auth@tests.example", password_hash="hash", role="patient", is_active=True,
    )
    db_session.add_all([user, duplicate_email_user])
    await db_session.flush()
    patient = Patient(
        user_id=user.id, first_name="Auth", last_name="Patient", date_of_birth=datetime(1990, 1, 1), gender="unknown",
        emergency_contact="", emergency_contact_name="",
    )
    db_session.add(patient)
    await db_session.commit()
    headers = {"Authorization": f"Bearer {create_access_token(subject=user.id, claims={'role': user.role})}"}
    return {"user": user, "patient": patient, "headers": headers}


def registration_payload(**overrides):
    return {
        "phone": "+919800007799", "email": "new.auth@tests.example", "first_name": "New",
        "last_name": "Patient", "password": "A-strong-password-123!", "gender": "unknown",
        "emergency_contact": "9876543210", "emergency_contact_name": "Family",
        **overrides,
    }


@pytest.mark.asyncio
async def test_register_creates_patient_with_hashed_password(async_client: AsyncClient, db_session):
    response = await async_client.post("/api/v1/auth/register", json=registration_payload())
    user = (await db_session.execute(select(User).where(User.phone == "+919800007799"))).scalar_one()
    patient = (await db_session.execute(select(Patient).where(Patient.user_id == user.id))).scalar_one()
    assert response.status_code == 201
    assert response.json() == {"message": "User registered successfully", "phone": "+919800007799"}
    assert user.role == "patient" and user.password_hash != "A-strong-password-123!"
    assert patient.first_name == "New" and patient.emergency_contact_name == "Family"


@pytest.mark.asyncio
async def test_register_rejects_duplicate_phone_and_email(async_client: AsyncClient, auth_api_context):
    ctx = auth_api_context
    duplicate_phone = await async_client.post("/api/v1/auth/register", json=registration_payload(phone=ctx["user"].phone))
    duplicate_email = await async_client.post("/api/v1/auth/register", json=registration_payload(email="duplicate.auth@tests.example"))
    assert (duplicate_phone.status_code, duplicate_phone.json()["detail"]) == (400, "A user with this phone number already exists.")
    assert (duplicate_email.status_code, duplicate_email.json()["detail"]) == (400, "A user with this email address already exists.")


@pytest.mark.asyncio
async def test_login_returns_tokens_and_persists_refresh_token(async_client: AsyncClient, auth_api_context, db_session):
    user = auth_api_context["user"]
    response = await async_client.post("/api/v1/auth/login", data={"username": user.email, "password": "Correct-password-123!"})
    body = response.json()
    stored = (await db_session.execute(select(RefreshToken).where(RefreshToken.user_id == user.id))).scalar_one()
    assert response.status_code == 200 and body["token_type"] == "bearer"
    assert body["access_token"] and body["refresh_token"]
    assert stored.token_hash and stored.revoked_at is None


@pytest.mark.asyncio
async def test_login_rejects_wrong_password_and_unknown_identifier(async_client: AsyncClient, auth_api_context):
    wrong = await async_client.post("/api/v1/auth/login", data={"username": auth_api_context["user"].phone, "password": "wrong"})
    missing = await async_client.post("/api/v1/auth/login", data={"username": "missing@tests.example", "password": "wrong"})
    expected = {"detail": "Incorrect email/phone number or password."}
    assert (wrong.status_code, wrong.json()) == (400, expected)
    assert (missing.status_code, missing.json()) == (400, expected)


@pytest.mark.asyncio
async def test_current_user_read_and_update_checks_duplicate_phone(async_client: AsyncClient, auth_api_context):
    ctx = auth_api_context
    current = await async_client.get("/api/v1/auth/me", headers=ctx["headers"])
    updated = await async_client.put("/api/v1/auth/me", headers=ctx["headers"], json={"phone": " 9800007703 "})
    duplicate = await async_client.put("/api/v1/auth/me", headers=ctx["headers"], json={"phone": "9800007702"})
    assert current.json() == {"id": ctx["user"].id, "phone": "9800007701", "email": "auth.coverage@tests.example", "role": "patient", "is_verified": True}
    assert updated.json() == {"id": ctx["user"].id, "phone": "9800007703", "email": "auth.coverage@tests.example"}
    assert (duplicate.status_code, duplicate.json()["detail"]) == (409, "This phone number is already in use.")


@pytest.mark.asyncio
async def test_refresh_rotates_persisted_token_and_rejects_revoked(async_client: AsyncClient, auth_api_context, db_session):
    user = auth_api_context["user"]
    old_token = create_refresh_token(subject=user.id, claims={"role": "patient", "patient_id": auth_api_context["patient"].id})
    stored = RefreshToken(
        user_id=user.id,
        token_hash=hashlib.sha256(old_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30),
    )
    db_session.add(stored)
    await db_session.commit()
    refreshed = await async_client.post("/api/v1/auth/refresh", params={"refresh_token": old_token})
    await db_session.refresh(stored)
    revoked = await async_client.post("/api/v1/auth/refresh", params={"refresh_token": old_token})
    assert refreshed.status_code == 200 and refreshed.json()["refresh_token"] != old_token
    assert stored.revoked_at is not None
    assert (revoked.status_code, revoked.json()["detail"]) == (401, "Refresh token is invalid or expired.")


@pytest.mark.asyncio
async def test_refresh_rejects_unavailable_user_and_logout_revokes_tokens(async_client: AsyncClient, auth_api_context, db_session):
    ctx = auth_api_context
    inactive = User(phone="9800007704", email="inactive.auth@tests.example", password_hash="hash", role="staff", is_active=False)
    db_session.add(inactive)
    await db_session.flush()
    token = create_refresh_token(subject=inactive.id, claims={"role": "staff"})
    db_session.add(RefreshToken(
        user_id=inactive.id, token_hash=hashlib.sha256(token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30),
    ))
    await db_session.commit()
    unavailable = await async_client.post("/api/v1/auth/refresh", params={"refresh_token": token})
    assert (unavailable.status_code, unavailable.json()["detail"]) == (401, "Account is unavailable.")

    active_token = create_refresh_token(subject=ctx["user"].id, claims={"role": "patient"})
    active_row = RefreshToken(
        user_id=ctx["user"].id, token_hash=hashlib.sha256(active_token.encode()).hexdigest(),
        expires_at=datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30),
    )
    db_session.add(active_row)
    await db_session.commit()
    logout = await async_client.post("/api/v1/auth/logout", headers=ctx["headers"])
    await db_session.refresh(active_row)
    assert logout.json() == {"message": "Logged out successfully"}
    assert active_row.revoked_at is not None
