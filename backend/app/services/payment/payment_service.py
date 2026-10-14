import hmac
import hashlib
import httpx
from typing import Dict, Any, Optional
from fastapi import HTTPException, status

from app.core.config import settings

class PaymentService:
    def __init__(self) -> None:
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET

    async def create_order(self, amount_in_inr: float, currency: str = "INR", receipt: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a payment order via Razorpay API.
        """
        if amount_in_inr <= 0 or not receipt:
            raise HTTPException(status_code=422, detail="A positive amount and invoice receipt are required.")
        amount_in_paise = int(amount_in_inr * 100)
        if not self.key_id or not self.key_secret:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Payment processing is not configured.",
            )

        auth = (self.key_id, self.key_secret)
        payload = {
            "amount": amount_in_paise,
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            res = await client.post("https://api.razorpay.com/v1/orders", json=payload, auth=auth)
            res.raise_for_status()
            return res.json()

    def verify_payment_signature(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Verify digital signature for Razorpay webhook/client payment completion using HMAC SHA256.
        """
        if not self.key_secret:
            return False

        msg = f"{order_id}|{payment_id}".encode("utf-8")
        generated_signature = hmac.new(
            self.key_secret.encode("utf-8"),
            msg,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(generated_signature, signature)

    def verify_payment(self, order_id: str, payment_id: str, signature: str) -> bool:
        """
        Alias for verify_payment_signature
        """
        return self.verify_payment_signature(order_id, payment_id, signature)

payment_service = PaymentService()
