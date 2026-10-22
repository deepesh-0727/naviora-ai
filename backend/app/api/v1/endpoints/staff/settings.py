from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.operations import RegisteredDevice, StaffSetting
from app.models.user import User

router = APIRouter()
STAFF_ROLES = ["doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff"]


class SettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    preferences: dict[str, object] | None = None
    push_notifications: bool | None = None
    sms_notifications: bool | None = None
    email_notifications: bool | None = None
    voice_assistant_enabled: bool | None = None
    analytics_enabled: bool | None = None


async def _setting(db: AsyncSession, user_id: int) -> StaffSetting | None:
    result = await db.execute(select(StaffSetting).where(StaffSetting.user_id == user_id))
    return result.scalar_one_or_none()


async def _response(db: AsyncSession, user_id: int, preferences: dict[str, object]) -> dict[str, object]:
    result = await db.execute(select(RegisteredDevice).where(RegisteredDevice.user_id == user_id, RegisteredDevice.is_active.is_(True)).order_by(RegisteredDevice.last_seen.desc()))
    devices = result.scalars().all()
    return {
        **preferences,
        "devices": [{"id": device.id, "name": device.name, "platform": device.platform, "last_seen": device.last_seen} for device in devices],
    }


@router.get("/settings")
async def get_staff_settings(
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    setting = await _setting(db, current_user.id)
    defaults = {
        "push_notifications": True,
        "sms_notifications": True,
        "email_notifications": True,
        "voice_assistant_enabled": True,
        "analytics_enabled": False,
    }
    preferences = {**defaults, **(setting.preferences if setting else {})}
    return await _response(db, current_user.id, preferences)


@router.put("/settings")
async def update_staff_settings(
    payload: SettingsUpdate,
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    changes = payload.model_dump(exclude_none=True)
    changes.pop("devices", None)
    preferences = changes.pop("preferences", {})
    if not isinstance(preferences, dict):
        raise HTTPException(status_code=422, detail="Preferences must be an object.")
    setting = await _setting(db, current_user.id)
    current = dict(setting.preferences) if setting else {}
    current.update(preferences)
    current.update(changes)
    if setting is None:
        setting = StaffSetting(user_id=current_user.id, preferences=current)
        db.add(setting)
    else:
        setting.preferences = current
    await db.commit()
    return await _response(db, current_user.id, current)


@router.delete("/devices/{device_id}")
async def deactivate_device(
    device_id: int,
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(RegisteredDevice).where(RegisteredDevice.id == device_id, RegisteredDevice.user_id == current_user.id, RegisteredDevice.is_active.is_(True)))
    device = result.scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Active registered device not found.")
    device.is_active = False
    await db.commit()
    return {"id": device.id, "is_active": False}
