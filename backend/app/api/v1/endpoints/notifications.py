from datetime import datetime, timezone
import hashlib

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import update, delete

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
            Notification.is_read.is_(False)
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
        raise HTTPException(status_code=404, detail="Notification not found.")
    notif.is_read = True
    notif.read_at = datetime.now(timezone.utc).replace(tzinfo=None)
    await db.commit()
    return {"message": "Marked as read"}

@router.put("/read-all")
async def mark_all_as_read(
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    await db.execute(
        update(Notification)
        .where(Notification.user_id == current_user.id, Notification.is_read.is_(False))
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
        raise HTTPException(status_code=404, detail="Notification not found.")
    await db.commit()
    return {"message": "Notification deleted"}

class TokenRegisterRequest(BaseModel):
    token: str
    platform: str = "android"

@router.post("/register-token")
async def register_device_token(
    request: TokenRegisterRequest,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    from app.core.encryption import encrypt_text
    from app.models.operations import RegisteredDevice
    token_hash = hashlib.sha256(request.token.encode("utf-8")).hexdigest()
    result = await db.execute(
        select(RegisteredDevice).filter(RegisteredDevice.token_hash == token_hash)
    )
    token_entry = result.scalars().first()
    if token_entry:
        token_entry.user_id = current_user.id
        token_entry.platform = request.platform
        token_entry.name = f"{request.platform} device"
        token_entry.token_encrypted = encrypt_text(request.token)
        token_entry.is_active = True
        token_entry.last_seen = datetime.now(timezone.utc).replace(tzinfo=None)
    else:
        new_token = RegisteredDevice(
            user_id=current_user.id,
            token_hash=token_hash,
            token_encrypted=encrypt_text(request.token),
            platform=request.platform,
            name=f"{request.platform} device",
        )
        db.add(new_token)
    await db.commit()
    return {"message": "Token registered"}

@router.delete("/unregister-token/{token}")
async def unregister_device_token(
    token: str,
    current_user = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    import hashlib
    from app.models.operations import RegisteredDevice
    await db.execute(
        delete(RegisteredDevice).where(
            RegisteredDevice.token_hash == hashlib.sha256(token.encode("utf-8")).hexdigest(),
            RegisteredDevice.user_id == current_user.id,
        )
    )
    await db.commit()
    return {"message": "Token unregistered"}
