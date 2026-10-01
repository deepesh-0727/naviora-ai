import asyncio
import logging
import httpx
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    def __init__(self, max_retries: int = 3) -> None:
        self.max_retries = max_retries

    async def _send(self, to_email: str, subject: str, content_html: str) -> bool:
        if not settings.EMAIL_API_KEY:
            logger.warning(f"[DEV MODE] SendGrid API key not set. Email to {to_email}: Subject '{subject}'")
            return True

        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": settings.EMAIL_FROM or "noreply@naviora.ai", "name": "Naviora AI Hospital"},
            "subject": subject,
            "content": [{"type": "text/html", "value": content_html}]
        }
        headers = {
            "Authorization": f"Bearer {settings.EMAIL_API_KEY}",
            "Content-Type": "application/json"
        }

        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    res = await client.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)
                    res.raise_for_status()
                return True
            except httpx.HTTPError as exc:
                if attempt == self.max_retries - 1:
                    logger.error(f"SendGrid delivery failed to {to_email}: {exc}")
                    return False
                await asyncio.sleep(2**attempt)
        return False

    async def send_appointment_confirmation(self, to_email: str, patient_name: str, doctor_name: str, time_str: str) -> bool:
        subject = "Appointment Confirmation - Naviora AI Hospital"
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px; background-color: #f4f6f8;">
            <h2 style="color: #0EA5E9;">Naviora AI Hospital</h2>
            <p>Dear <strong>{patient_name}</strong>,</p>
            <p>Your appointment has been successfully booked with <strong>{doctor_name}</strong>.</p>
            <p><strong>Scheduled Time:</strong> {time_str}</p>
            <p>Please arrive 15 minutes prior to your scheduled time.</p>
            <br>
            <p style="color: #64748B;">Naviora AI Healthcare Systems</p>
        </div>
        """
        return await self._send(to_email, subject, html)

    async def send_billing_invoice(self, to_email: str, invoice_number: str, amount: float) -> bool:
        subject = f"Invoice #{invoice_number} - Naviora AI Hospital"
        html = f"""
        <div style="font-family: Arial, sans-serif; padding: 20px;">
            <h2 style="color: #0EA5E9;">Billing Receipt</h2>
            <p>Invoice Number: <strong>{invoice_number}</strong></p>
            <p>Total Amount: <strong>₹{amount:.2f}</strong></p>
            <p>Thank you for choosing Naviora AI Hospital.</p>
        </div>
        """
        return await self._send(to_email, subject, html)


    async def send_confirmation(self, to_email: str, patient_name: str, doctor_name: str, time_str: str) -> bool:
        return await self.send_appointment_confirmation(to_email, patient_name, doctor_name, time_str)

    async def send_invoice(self, to_email: str, invoice_number: str, amount: float) -> bool:
        return await self.send_billing_invoice(to_email, invoice_number, amount)


email_service = EmailService()
