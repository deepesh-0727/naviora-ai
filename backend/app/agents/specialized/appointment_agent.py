import logging
import json
from typing import Dict, Any
from ..base_agent import BaseAgent

logger = logging.getLogger(__name__)

class AppointmentAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Appointment Specialist for Naviora AI. "
            "Your job is to take a raw user query and extract specific appointment details. "
            "You MUST output JSON with fields: 'doctor_specialty', 'preferred_time', 'symptoms', 'is_urgent', 'is_checkin'."
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
            f"  \"is_urgent\": <boolean>,\n"
            f"  \"is_checkin\": <boolean_true_if_patient_is_arriving_now>\n"
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
            logger.warning(f"AppointmentAgent using heuristic extraction: {e}")
            query_lower = user_query.lower()
            specialty = "Cardiology" if "cardio" in query_lower or "heart" in query_lower else ("Pediatrics" if "child" in query_lower or "pediatric" in query_lower else ("Orthopedics" if "bone" in query_lower or "ortho" in query_lower else "General Medicine"))
            return {
                "doctor_specialty": specialty,
                "preferred_time": "Tomorrow 10:00 AM",
                "symptoms": user_query,
                "is_urgent": "urgent" in query_lower or "soon" in query_lower,
                "is_checkin": any(w in query_lower for w in ["check in", "i am here", "arrived", "reached"])
            }
