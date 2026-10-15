import datetime

import pytest
from sqlalchemy import select

from app.core.security import verify_password
from app.models.patient import Patient
from app.models.user import User
from app.schemas.auth import UserRegister
from app.services.auth_service import auth_service


def registration_payload(**changes):
    values = {
        "phone": "+919800000301",
        "email": "auth-service@tests.example",
        "first_name": "Asha",
        "last_name": "Rao",
        "password": "StrongPass!301",
        "date_of_birth": datetime.date(1990, 4, 12),
    }
    values.update(changes)
    return UserRegister(**values)


@pytest.mark.asyncio
async def test_auth_register_valid_patient_persists_hashed_password_and_profile(db_session):
    user = await auth_service.register_patient(db_session, registration_payload())

    assert user.id is not None
    assert user.role == "patient"
    assert user.password_hash != "StrongPass!301"
    assert verify_password("StrongPass!301", user.password_hash)
    profile = await db_session.scalar(select(Patient).where(Patient.user_id == user.id))
    assert profile is not None
    assert profile.first_name == "Asha"
    assert profile.last_name == "Rao"


@pytest.mark.asyncio
async def test_authenticate_user_accepts_email_case_insensitively(db_session):
    user = await auth_service.register_patient(db_session, registration_payload())

    authenticated = await auth_service.authenticate_user(db_session, "AUTH-SERVICE@TESTS.EXAMPLE", "StrongPass!301")

    assert authenticated is not None
    assert authenticated.id == user.id


@pytest.mark.asyncio
async def test_authenticate_user_rejects_wrong_password(db_session):
    await auth_service.register_patient(db_session, registration_payload())

    authenticated = await auth_service.authenticate_user(db_session, "+919800000301", "wrong-password")

    assert authenticated is None


@pytest.mark.asyncio
async def test_auth_get_user_by_phone_returns_persisted_user(db_session):
    expected = await auth_service.register_patient(db_session, registration_payload())

    actual = await auth_service.get_user_by_phone(db_session, "+919800000301")

    assert actual is not None
    assert actual.id == expected.id
