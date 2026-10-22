from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.api.v1.endpoints.admin.health import _probe
from app.db.session import get_db
from app.models.operations import SystemSetting
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]
SAFE_SETTING_KEYS = {"maintenance_mode", "appointment_booking_enabled", "default_language", "support_contact", "hospital_profile"}


class SettingUpdate(BaseModel):
    key: str = Field(min_length=2, max_length=120)
    value: dict[str, object]


class IntegrationTest(BaseModel):
    service: str = Field(pattern="^(database|redis|rabbitmq)$")


@router.get("")
async def list_settings(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(SystemSetting).where(SystemSetting.key.in_(SAFE_SETTING_KEYS)).order_by(SystemSetting.key))
    return {"items": [{"key": row.key, "value": row.value, "updated_at": row.updated_at} for row in result.scalars().all()]}


@router.put("")
async def update_setting(payload: SettingUpdate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if payload.key not in SAFE_SETTING_KEYS:
        raise HTTPException(status_code=422, detail="Setting key is not editable through this API.")
    result = await db.execute(select(SystemSetting).where(SystemSetting.key == payload.key))
    setting = result.scalar_one_or_none()
    if setting is None:
        setting = SystemSetting(key=payload.key, value=payload.value, updated_by_id=current_user.id)
        db.add(setting)
    else:
        setting.value = payload.value
        setting.updated_by_id = current_user.id
    await db.commit()
    await db.refresh(setting)
    return {"key": setting.key, "value": setting.value, "updated_at": setting.updated_at}


@router.post("/test-integration")
async def test_integration(payload: IntegrationTest, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    try:
        return await _probe(payload.service, db)
    except Exception as exc:
        return {"service": payload.service, "reachable": False, "detail": str(exc)}
