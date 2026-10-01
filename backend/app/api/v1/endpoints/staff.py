from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.doctor import Doctor
from app.models.user import User

router = APIRouter()
STAFF_ROLES = {"doctor", "staff", "nurse", "admin"}


class StaffProfileUpdate(BaseModel):
    email: EmailStr | None = None
    phone: str | None = Field(None, min_length=1, max_length=20)


class StaffProfileResponse(BaseModel):
    id: int
    email: str
    phone: str
    role: str
    is_active: bool
    doctor_profile: dict | None = None

    model_config = ConfigDict(from_attributes=True)


async def _staff_profile(user: User, db: AsyncSession) -> dict:
    profile = None
    if user.role == "doctor":
        result = await db.execute(select(Doctor).where(Doctor.user_id == user.id))
        doctor = result.scalar_one_or_none()
        if not doctor:
            raise HTTPException(status_code=404, detail="Doctor profile not found.")
        profile = {
            "id": doctor.id,
            "first_name": doctor.first_name,
            "last_name": doctor.last_name,
            "specialization": doctor.specialization,
            "department_id": doctor.department_id,
        }
    return {
        "id": user.id,
        "email": user.email,
        "phone": user.phone,
        "role": user.role,
        "is_active": user.is_active,
        "doctor_profile": profile,
    }


@router.get("/profile", response_model=StaffProfileResponse)
async def get_staff_profile(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff profile access is not authorized.")
    return await _staff_profile(current_user, db)


@router.put("/profile", response_model=StaffProfileResponse)
async def update_staff_profile(
    update: StaffProfileUpdate,
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    if current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Staff profile access is not authorized.")

    changes = update.model_dump(exclude_unset=True, exclude_none=True)
    if not changes:
        raise HTTPException(status_code=422, detail="At least one profile field is required.")

    if "email" in changes:
        email = str(changes["email"])
        duplicate = await db.execute(
            select(User.id).where(User.email == email, User.id != current_user.id)
        )
        if duplicate.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Email address is already in use.")
        current_user.email = email
    if "phone" in changes:
        phone = changes["phone"]
        duplicate = await db.execute(
            select(User.id).where(User.phone == phone, User.id != current_user.id)
        )
        if duplicate.scalar_one_or_none() is not None:
            raise HTTPException(status_code=409, detail="Phone number is already in use.")
        current_user.phone = phone

    await db.commit()
    await db.refresh(current_user)
    return await _staff_profile(current_user, db)
