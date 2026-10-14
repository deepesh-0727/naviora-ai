import logging
import json
from typing import Dict, Any
from ..base_agent import BaseAgent

logger = logging.getLogger(__name__)

class PharmacyAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Pharmacy Assistant for Naviora AI. "
            "Your job is to answer questions about medications, availability, and dosage. "
            "Extract: 'medication_name', 'query_type' (availability/dosage/reminder), 'quantity'."
        )
        super().__init__(name="PharmacyAgent", system_prompt=system_prompt, ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("PharmacyAgent processing a request")

        prompt = (
            f"Extract pharmacy details from the following query:\n"
            f"Query: \"{user_query}\"\n\n"
            f"Context: {json.dumps(context)}\n\n"
            f"Output JSON ONLY:\n"
            f"{{\n"
            f"  \"medication_name\": \"<medication_name_or_null>\",\n"
            f"  \"query_type\": \"<availability/dosage/reminder/unknown>\",\n"
            f"  \"quantity\": \"<quantity_if_present_or_null>\"\n"
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
            logger.warning("Pharmacy extraction unavailable: %s", type(e).__name__)
            return {
                "medication_name": None,
                "query_type": "unknown",
                "quantity": None,
            }
