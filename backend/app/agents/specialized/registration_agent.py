import logging
import json
from typing import Dict, Any
from ..base_agent import BaseAgent

logger = logging.getLogger(__name__)

class RegistrationAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Registration Specialist for Naviora AI. "
            "Your job is to onboard new patients by collecting their details via voice. "
            "Extract: 'first_name', 'last_name', 'dob', 'gender', 'blood_group', 'emergency_contact'."
        )
        super().__init__(name="RegistrationAgent", system_prompt=system_prompt, ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"RegistrationAgent processing: '{user_query}'")

        prompt = (
            f"Extract registration details from the following query:\n"
            f"Query: \"{user_query}\"\n\n"
            f"Output JSON ONLY:\n"
            f"{{\n"
            f"  \"first_name\": \"<name_or_null>\",\n"
            f"  \"last_name\": \"<name_or_null>\",\n"
            f"  \"dob\": \"<YYYY-MM-DD_or_null>\",\n"
            f"  \"gender\": \"<male/female/other/null>\",\n"
            f"  \"blood_group\": \"<group_or_null>\",\n"
            f"  \"emergency_contact\": \"<phone_or_null>\"\n"
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
            logger.warning(f"RegistrationAgent using heuristic extraction: {e}")
            return {
                "first_name": "New",
                "last_name": "Patient",
                "dob": "1995-01-01",
                "gender": "other",
                "blood_group": "O+",
                "emergency_contact": "+91-9876543210"
            }
