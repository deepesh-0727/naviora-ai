import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    async def _send(self, phone: str, message: str) -> bool:
        if not settings.TEXTLOCAL_API_KEY:
            logger.warning(f"[DEV MODE] SMS API Key not set. Message to {phone}: '{message}'")
            return True

        payload = {
            "apikey": settings.TEXTLOCAL_API_KEY,
            "numbers": phone,
            "message": message,
            "sender": settings.SMS_SENDER,
        }
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post("https://api.textlocal.in/send", data=payload)
                    response.raise_for_status()
                return True
            except httpx.HTTPError:
                if attempt == self.max_retries - 1:
                    logger.exception("SMS delivery failed after retries")
                    return False
                await asyncio.sleep(2**attempt)
        return False

    async def send_otp(self, phone: str, code: str) -> bool:
        return await self._send(phone, f"Your Naviora AI verification code is {code}. It expires in 5 minutes.")

    async def send_appointment_reminder(self, phone: str, details: str) -> bool:
        return await self._send(phone, f"Naviora AI appointment reminder: {details}")


sms_service = SMSService()