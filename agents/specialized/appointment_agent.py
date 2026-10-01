import logging
import json
from typing import Dict, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AppointmentAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Appointment Specialist for Naviora AI. "
            "Your job is to take a raw user query and extract specific appointment details. "
            "You MUST output JSON with fields: 'doctor_specialty', 'preferred_time', 'symptoms', 'is_urgent'."
        )
        super().__init__(name="AppointmentAgent", system_prompt=system_prompt, ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"AppointmentAgent processing: '{user_query}'")

        prompt = (
            f"Extract appointment details from the following query:\n"
            f"Query: \"{user_query}\"\n\n"
            f"Context: {json.dumps(context)}\n\n"
            f"Output JSON ONLY:\n"
            f"{{\n"
            f"  \"doctor_specialty\": \"<specialty_or_null>\",\n"
            f"  \"preferred_time\": \"<time_or_date_or_null>\",\n"
            f"  \"symptoms\": \"<brief_symptoms_or_null>\",\n"
            f"  \"is_urgent\": <boolean>\n"
            f"}}"
        )

        response_text = await self.call_llm(prompt=prompt)

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            return json.loads(response_text[json_start:json_end])
        except Exception as e:
            logger.error(f"AppointmentAgent failed to parse JSON: {e}")
            return {
                "doctor_specialty": None,
                "preferred_time": None,
                "symptoms": None,
                "is_urgent": False
            }
