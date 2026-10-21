from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.doctor import Department, Doctor
from app.models.nurse import NurseProfile
from app.models.user import User

router = APIRouter()


class StaffCreate(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=12, max_length=128)
    role: Literal["doctor", "nurse", "admin"]
    department_id: int | None = None
    specialization: str | None = Field(default=None, min_length=2, max_length=100)
    license_number: str | None = Field(default=None, min_length=1, max_length=50)
    years_of_experience: int | None = Field(default=None, ge=0, le=80)


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_staff(
    payload: StaffCreate,
    current_user: User = Depends(deps.check_role(["admin", "super_admin"])),
    db: AsyncSession = Depends(get_db),
):
    if payload.role == "doctor":
        if not all((payload.department_id, payload.specialization, payload.license_number)) or payload.years_of_experience is None:
            raise HTTPException(status_code=422, detail="Doctor accounts require department, specialization, license, and experience fields.")
    if payload.role == "nurse" and payload.department_id is not None:
        if await db.get(Department, payload.department_id) is None:
            raise HTTPException(status_code=404, detail="Department not found.")

    existing = await db.scalar(
        select(User.id).where((User.email == str(payload.email)) | (User.phone == payload.phone))
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email or phone number is already registered.")

    department = None
    if payload.role == "doctor":
        department = await db.get(Department, payload.department_id)
        if department is None:
            raise HTTPException(status_code=404, detail="Department not found.")
        duplicate_license = await db.scalar(select(Doctor.id).where(Doctor.license_number == payload.license_number))
        if duplicate_license is not None:
            raise HTTPException(status_code=409, detail="License number is already registered.")

    user = User(
        email=str(payload.email),
        phone=payload.phone,
        password_hash=get_password_hash(payload.password),
        role=payload.role,
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    await db.flush()

    if payload.role == "doctor":
        db.add(Doctor(
            user_id=user.id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            specialization=payload.specialization,
            department_id=department.id,
            license_number=payload.license_number,
            years_of_experience=payload.years_of_experience,
        ))
    elif payload.role == "nurse":
        db.add(NurseProfile(
            user_id=user.id,
            first_name=payload.first_name.strip(),
            last_name=payload.last_name.strip(),
            department_id=payload.department_id,
        ))

    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=409, detail="Email, phone, or profile details conflict with an existing account.") from exc
    await db.refresh(user)
    return {
        "id": user.id,
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
    }
