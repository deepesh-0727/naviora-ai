from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.communication import Notification
from app.models.user import User

router = APIRouter()
STAFF_ROLES = ["doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff"]


@router.get("")
async def staff_notifications(
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).where(Notification.user_id == current_user.id).order_by(Notification.created_at.desc()))
    return {"items": result.scalars().all()}


@router.put("/{notification_id}/read")
async def mark_staff_notification_read(
    notification_id: int,
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Notification).where(Notification.id == notification_id, Notification.user_id == current_user.id))
    notification = result.scalar_one_or_none()
    if notification is None:
        raise HTTPException(status_code=404, detail="Notification not found.")
    notification.is_read = True
    notification.read_at = datetime.utcnow()
    await db.commit()
    return {"id": notification.id, "is_read": notification.is_read, "read_at": notification.read_at}
