import logging
import httpx
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings

logger = logging.getLogger(__name__)


class PushNotificationService:
    def __init__(self) -> None:
        self.fcm_url = "https://fcm.googleapis.com/fcm/send"

    async def send_push_notification_to_user(
        self,
        db: AsyncSession,
        user_id: int,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        from sqlalchemy import select
        from app.core.encryption import decrypt_text
        from app.models.operations import RegisteredDevice
        result = await db.execute(
            select(RegisteredDevice).where(
                RegisteredDevice.user_id == user_id,
                RegisteredDevice.is_active.is_(True),
                RegisteredDevice.token_encrypted.is_not(None),
            )
        )
        tokens = result.scalars().all()
        success = False
        for device in tokens:
            try:
                token = decrypt_text(device.token_encrypted)
            except RuntimeError:
                logger.exception("Could not decrypt registered push token for device %s", device.id)
                continue
            if await self.send_push_notification(token, title, body, data):
                success = True
        return success

    async def send_push_notification(
        self,
        token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None
    ) -> bool:
        if not settings.FIREBASE_CREDENTIALS:
            logger.error("Firebase credentials are not configured; push delivery was not attempted.")
            return False

        headers = {
            "Authorization": f"key={settings.FIREBASE_CREDENTIALS}",
            "Content-Type": "application/json"
        }
        payload = {
            "to": token,
            "notification": {
                "title": title,
                "body": body,
                "sound": "default"
            },
            "data": data or {}
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                res = await client.post(self.fcm_url, json=payload, headers=headers)
                return res.status_code == 200
        except Exception as exc:
            logger.error(f"FCM Push failed: {exc}")
            return False

    async def send_queue_update(self, token: str, position: int, est_wait: int) -> bool:
        title = "Naviora Queue Update"
        body = f"You are now #{position} in queue. Estimated wait time: {est_wait} mins."
        return await self.send_push_notification(token, title, body, {"type": "queue_update", "position": position})

    async def send_emergency_alert(self, token: str, location_str: str) -> bool:
        title = "🚨 EMERGENCY ALERT DISPATCHED"
        body = f"Emergency staff dispatched to location: {location_str}"
        return await self.send_push_notification(token, title, body, {"type": "emergency"})


push_service = PushNotificationService()
