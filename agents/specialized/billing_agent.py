import json
import logging
from typing import Any, Dict

from ..base_agent import BaseAgent

logger = logging.getLogger(__name__)


class BillingAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Billing & Payment Specialist for Naviora AI. "
            "Your job is to answer queries about invoices, payments, insurance claims, and estimations. "
            "Extract: 'query_type' (invoice_status/payment_method/insurance_claim/estimation), 'amount_mentioned'."
        )
        super().__init__(name="BillingAgent", system_prompt=system_prompt, ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"BillingAgent processing: '{user_query}'")
        prompt = (
            f"Analyze the following billing query:\n"
            f"Query: \"{user_query}\"\n\n"
            f"Output JSON ONLY:\n"
            f"{{\n"
            f"  \"query_type\": \"<type>\",\n"
            f"  \"amount_mentioned\": <float_or_null>,\n"
            f"  \"is_payment_intent\": <boolean>\n"
            f"}}"
        )
        try:
            response_text = await self.call_llm(prompt=prompt)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            return json.loads(response_text[json_start:json_end] if json_start != -1 else response_text)
        except Exception as error:
            logger.warning(f"BillingAgent using heuristic extraction: {error}")
            query_lower = user_query.lower()
            if any(word in query_lower for word in ("cost", "estimate", "price")):
                query_type = "estimation"
            elif any(word in query_lower for word in ("pay", "upi", "card")):
                query_type = "payment_method"
            else:
                query_type = "invoice_status"
            return {
                "query_type": query_type,
                "amount_mentioned": 1500.0,
                "is_payment_intent": "pay" in query_lower,
            }