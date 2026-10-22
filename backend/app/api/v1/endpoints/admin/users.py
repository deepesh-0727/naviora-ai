from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.core.security import get_password_hash
from app.db.session import get_db
from app.models.doctor import Department, Doctor
from app.models.nurse import NurseProfile
from app.models.operations import RegisteredDevice
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]
MANAGED_ROLES = {"patient", "doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff", "admin"}


class UserCreate(BaseModel):
    email: EmailStr
    phone: str = Field(min_length=7, max_length=20)
    password: str = Field(min_length=12, max_length=128)
    role: str
    first_name: str | None = None
    last_name: str | None = None
    specialization: str | None = None
    department_id: int | None = None
    license_number: str | None = None
    years_of_experience: int | None = Field(default=None, ge=0, le=80)


class UserUpdate(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=7, max_length=20)


class PasswordReset(BaseModel):
    password: str = Field(min_length=12, max_length=128)


@router.get("")
async def list_users(
    role: str | None = None,
    current_user: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    query = select(User).order_by(User.id)
    if role:
        query = query.where(User.role == role)
    result = await db.execute(query)
    return {"items": [{"id": user.id, "first_name": user.first_name, "last_name": user.last_name, "email": user.email, "phone": user.phone, "role": user.role, "is_active": user.is_active, "created_at": user.created_at} for user in result.scalars().all()]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    current_user: User = Depends(deps.check_role(ADMIN_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    if payload.role not in MANAGED_ROLES:
        raise HTTPException(status_code=422, detail="Unsupported role.")
    if payload.role == "doctor" and not all([payload.first_name, payload.last_name, payload.specialization, payload.department_id, payload.license_number, payload.years_of_experience is not None]):
        raise HTTPException(status_code=422, detail="Doctor accounts require profile, department, and license fields.")
    if payload.role == "nurse" and not all([payload.first_name, payload.last_name]):
        raise HTTPException(status_code=422, detail="Nurse accounts require first and last names.")
    existing = await db.scalar(select(User.id).where((User.email == str(payload.email)) | (User.phone == payload.phone)))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email or phone number is already registered.")
    user = User(email=str(payload.email), phone=payload.phone, password_hash=get_password_hash(payload.password), role=payload.role, first_name=payload.first_name, last_name=payload.last_name, is_active=True, is_verified=True)
    db.add(user)
    await db.flush()
    if payload.role == "doctor":
        department = await db.get(Department, payload.department_id)
        if department is None:
            raise HTTPException(status_code=404, detail="Department not found.")
        doctor = Doctor(
            user_id=user.id,
            first_name=payload.first_name or "",
            last_name=payload.last_name or "",
            specialization=payload.specialization or "",
            department_id=department.id,
            license_number=payload.license_number or "",
            years_of_experience=payload.years_of_experience or 0,
        )
        db.add(doctor)
    elif payload.role == "nurse":
        if payload.department_id is not None and await db.get(Department, payload.department_id) is None:
            raise HTTPException(status_code=404, detail="Department not found.")
        db.add(NurseProfile(user_id=user.id, first_name=payload.first_name or "", last_name=payload.last_name or "", department_id=payload.department_id))
    await db.commit()
    await db.refresh(user)
    return {"id": user.id, "email": user.email, "phone": user.phone, "role": user.role, "is_active": user.is_active}


@router.get("/{user_id}")
async def get_user(user_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    return {"id": user.id, "email": user.email, "phone": user.phone, "role": user.role, "is_active": user.is_active, "created_at": user.created_at, "last_login": user.last_login}


@router.put("/{user_id}")
async def update_user(user_id: int, payload: UserUpdate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    updates = payload.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] not in MANAGED_ROLES:
        raise HTTPException(status_code=422, detail="Unsupported role.")
    if user.id == current_user.id and updates.get("role", user.role) != user.role:
        raise HTTPException(status_code=409, detail="You cannot change your own administrator role.")
    if updates.get("role") == "doctor" and user.role != "doctor":
        has_profile = await db.scalar(select(Doctor.id).where(Doctor.user_id == user.id))
        if has_profile is None:
            raise HTTPException(status_code=409, detail="Create a doctor account with its profile fields before assigning the doctor role.")
    if updates.get("role") == "nurse" and user.role != "nurse":
        has_profile = await db.scalar(select(NurseProfile.id).where(NurseProfile.user_id == user.id))
        if has_profile is None:
            raise HTTPException(status_code=409, detail="Create a nurse account with its profile fields before assigning the nurse role.")
    if "email" in updates:
        email = str(updates["email"])
        exists = await db.scalar(select(User.id).where(User.email == email, User.id != user_id))
        if exists is not None:
            raise HTTPException(status_code=409, detail="Email address is already registered.")
        user.email = email
    if "phone" in updates:
        exists = await db.scalar(select(User.id).where(User.phone == updates["phone"], User.id != user_id))
        if exists is not None:
            raise HTTPException(status_code=409, detail="Phone number is already registered.")
        user.phone = updates["phone"]
    if "role" in updates and updates["role"] is not None:
        user.role = updates["role"]
    if "is_active" in updates and updates["is_active"] is not None:
        user.is_active = updates["is_active"]
    await db.commit()
    return {"id": user.id, "email": user.email, "phone": user.phone, "role": user.role, "is_active": user.is_active}


@router.delete("/{user_id}")
async def deactivate_user(user_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    if user.id == current_user.id:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own administrator account.")
    user.is_active = False
    await db.commit()
    return {"id": user.id, "is_active": False}


@router.post("/{user_id}/reset-password")
async def reset_password(user_id: int, payload: PasswordReset, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found.")
    user.password_hash = get_password_hash(payload.password)
    await db.commit()
    return {"id": user.id, "password_reset": True}


@router.get("/{user_id}/devices")
async def list_user_devices(user_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if await db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="User not found.")
    result = await db.execute(select(RegisteredDevice).where(RegisteredDevice.user_id == user_id).order_by(RegisteredDevice.last_seen.desc()))
    return {"items": [{"id": item.id, "name": item.name, "platform": item.platform, "is_active": item.is_active, "last_seen": item.last_seen} for item in result.scalars().all()]}


@router.delete("/devices/{device_id}")
async def delete_user_device(device_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    device = await db.get(RegisteredDevice, device_id)
    if device is None:
        raise HTTPException(status_code=404, detail="Device not found.")
    device.is_active = False
    await db.commit()
    return {"id": device.id, "is_active": False}
