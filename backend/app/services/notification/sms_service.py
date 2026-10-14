import asyncio
import logging

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class SMSService:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    async def _send(self, phone: str, message: str) -> bool:
        if settings.TWILIO_SID and settings.TWILIO_AUTH_TOKEN and settings.TWILIO_PHONE_NUMBER:
            endpoint = (
                "https://api.twilio.com/2010-04-01/Accounts/"
                f"{settings.TWILIO_SID}/Messages.json"
            )
            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=10.0) as client:
                        response = await client.post(
                            endpoint,
                            data={"To": phone, "From": settings.TWILIO_PHONE_NUMBER, "Body": message},
                            auth=(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN),
                        )
                        response.raise_for_status()
                    return True
                except httpx.HTTPError:
                    if attempt == self.max_retries - 1:
                        logger.exception("Twilio SMS delivery failed after retries")
                        return False
                    await asyncio.sleep(2**attempt)
            return False

        if not settings.TEXTLOCAL_API_KEY:
            logger.error("SMS delivery is not configured; refusing to report OTP as delivered.")
            return False

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

    async def send_otp(self, phone: str, code: str, expires_in_seconds: int = 300) -> bool:
        expiry_minutes = max(1, (expires_in_seconds + 59) // 60)
        message = f"Your Naviora AI verification code is {code}. It expires in {expiry_minutes} minute(s)."
        return await self._send(phone, message)

    async def send_appointment_reminder(self, phone: str, details: str) -> bool:
        return await self._send(phone, f"Naviora AI appointment reminder: {details}")


sms_service = SMSService()
