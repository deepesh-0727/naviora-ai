import logging
import json
from typing import Dict, Any
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
            if json_start != -1 and json_end != -1:
                return json.loads(response_text[json_start:json_end])
            return json.loads(response_text)
        except Exception as e:
            logger.warning(f"BillingAgent using heuristic extraction: {e}")
            query_lower = user_query.lower()
            q_type = "estimation" if "cost" in query_lower or "estimate" in query_lower or "price" in query_lower else ("payment_method" if "pay" in query_lower or "upi" in query_lower or "card" in query_lower else "invoice_status")
            return {"query_type": q_type, "amount_mentioned": 1500.0, "is_payment_intent": "pay" in query_lower}
