import hmac
import hashlib
import logging
import httpx
from typing import Dict, Any, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    def __init__(self) -> None:
        self.key_id = settings.RAZORPAY_KEY_ID
        self.key_secret = settings.RAZORPAY_KEY_SECRET

    async def create_order(self, amount_in_inr: float, currency: str = "INR", receipt: Optional[str] = None) -> Dict[str, Any]:
        """
        Create a payment order via Razorpay API.
        """
        amount_in_paise = int(amount_in_inr * 100)
        
        if not self.key_id or not self.key_secret:
            logger.warning(f"[DEV MODE] Razorpay keys unset. Simulating order for ₹{amount_in_inr}")
            import time
            mock_id = f"order_dev_{int(time.time())}"
            return {
                "id": mock_id,
                "entity": "order",
                "amount": amount_in_paise,
                "currency": currency,
                "receipt": receipt or mock_id,
                "status": "created"
            }

        auth = (self.key_id, self.key_secret)
        payload = {
            "amount": amount_in_paise,
            "currency": currency,
            "receipt": receipt or "rcpt_naviora",
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
            logger.warning("[DEV MODE] Auto-verifying signature in development environment")
            return True

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

    async def generate_invoice(self, order_id: str, payment_id: str, amount: float, customer_email: str) -> Dict[str, Any]:
        """
        Generate digital invoice details for payment.
        """
        return {
            "invoice_id": f"INV-{order_id[-8:]}",
            "order_id": order_id,
            "payment_id": payment_id,
            "amount": amount,
            "customer_email": customer_email,
            "status": "paid"
        }


payment_service = PaymentService()
