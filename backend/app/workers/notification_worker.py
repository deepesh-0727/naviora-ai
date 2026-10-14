import asyncio
import logging
import httpx
from typing import Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class NotificationWorker:
    """
    Enterprise Background Job Processor.
    Handles high-latency operations with built-in resilience and circuit breaking.
    """
    def __init__(self):
        self.max_retries = 3
        self.backoff_factor = 2.0

    async def send_sms(self, phone: str, message: str, priority: str = "normal"):
        """
        Sends critical SMS notifications via production-grade gateways.
        Includes retry logic for hospital-critical alerts.
        """
        payload = {
            "apikey": settings.TEXTLOCAL_API_KEY,
            "numbers": phone,
            "message": message,
            "sender": settings.SMS_SENDER
        }

        for attempt in range(self.max_retries):
            try:
                logger.info(f"SMS Dispatch [Attempt {attempt+1}]: target={phone}")
                if not settings.TEXTLOCAL_API_KEY:
                    logger.error("SMS provider is not configured; delivery was not attempted")
                    return False
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post("https://api.textlocal.in/send", data=payload)
                    response.raise_for_status()
                logger.info(f"SMS Delivered Successfully: {phone}")
                return True

            except Exception as e:
                logger.warning(f"SMS Failure: {str(e)}. Retrying in {self.backoff_factor**attempt}s...")
                await asyncio.sleep(self.backoff_factor ** attempt)

        logger.error(f"CRITICAL: Failed to deliver SMS to {phone} after {self.max_retries} attempts.")
        return False

    async def send_email(self, email: str, subject: str, body: str):
        """
        Sends HTML formatted clinical reports or confirmations.
        """
        if not settings.SENDGRID_API_KEY or not settings.EMAIL_FROM:
            logger.error("Email provider is not configured; delivery was not attempted")
            return False
        payload = {
            "personalizations": [{"to": [{"email": email}], "subject": subject}],
            "from": {"email": settings.EMAIL_FROM},
            "content": [{"type": "text/html", "value": body}],
        }
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                json=payload,
                headers={"Authorization": f"Bearer {settings.SENDGRID_API_KEY}"},
            )
            response.raise_for_status()
        return True

    async def generate_patient_report(self, patient_id: int, data: Dict[str, Any]):
        raise NotImplementedError("Patient report generation and storage are not implemented.")

worker = NotificationWorker()
