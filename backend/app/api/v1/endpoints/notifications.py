from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete
from typing import List

from app.db.session import get_db
from app.models.communication import Notification
from app.api import deps

router = APIRouter()

@router.get("")
@router.get("/")
async def list_notifications(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notification).filter(Notification.user_id == current_user.id)
    )
    return result.scalars().all()

@router.get("/unread")
async def get_unread_count(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Notification).filter(
            Notification.user_id == current_user.id,
            Notification.is_read == False
        )
    )
    return {"count": len(result.scalars().all())}

@router.put("/{id}/read")
async def mark_as_read(
    id: int,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Notification).filter(
        Notification.id == id,
        Notification.user_id == current_user.id,
    ))
    notif = result.scalars().first()
    if not notif:
        return {"message": "Notification not found"}
    notif.is_read = True
    await db.commit()
    return {"message": "Marked as read"}

@router.put("/read-all")
async def mark_all_as_read(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read == False)
        .values(is_read=True)
    )
    await db.commit()
    return {"message": "All notifications marked as read"}

@router.delete("/{id}")
async def delete_notification(
    id: int,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(delete(Notification).where(
        Notification.id == id,
        Notification.user_id == current_user.id,
    ))
    if result.rowcount == 0:
        return {"message": "Notification not found"}
    await db.commit()
    return {"message": "Notification deleted"}

from pydantic import BaseModel
class TokenRegisterRequest(BaseModel):
    token: str
    platform: str = "android"

@router.post("/register-token")
async def register_device_token(
    request: TokenRegisterRequest,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.models.communication import DeviceToken
    result = await db.execute(
        select(DeviceToken).filter(DeviceToken.token == request.token)
    )
    token_entry = result.scalars().first()
    if token_entry:
        if token_entry.user_id != current_user.id:
            token_entry.user_id = current_user.id
            await db.commit()
    else:
        new_token = DeviceToken(user_id=current_user.id, token=request.token, platform=request.platform)
        db.add(new_token)
        await db.commit()
    return {"message": "Token registered"}

@router.delete("/unregister-token/{token}")
async def unregister_device_token(
    token: str,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.models.communication import DeviceToken
    await db.execute(delete(DeviceToken).where(
        DeviceToken.token == token,
        DeviceToken.user_id == current_user.id
    ))
    await db.commit()
    return {"message": "Token unregistered"}
