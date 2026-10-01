import logging
import json
from typing import Dict, Any
from ..base_agent import BaseAgent

logger = logging.getLogger(__name__)

class NavigationAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Navigation Guide for Naviora AI. "
            "Your job is to understand where the patient is and where they want to go. "
            "Extract: 'destination', 'current_location', 'needs_elevator', 'is_urgent'."
        )
        super().__init__(name="NavigationAgent", system_prompt=system_prompt, ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"NavigationAgent processing: '{user_query}'")

        prompt = (
            f"Extract navigation details from the following query:\n"
            f"Query: \"{user_query}\"\n\n"
            f"Context: {json.dumps(context)}\n\n"
            f"Output JSON ONLY:\n"
            f"{{\n"
            f"  \"destination\": \"<department_or_room>\",\n"
            f"  \"current_location\": \"<current_landmark_if_known>\",\n"
            f"  \"needs_elevator\": <boolean>,\n"
            f"  \"is_urgent\": <boolean>\n"
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
            logger.warning(f"NavigationAgent using heuristic extraction: {e}")
            query_lower = user_query.lower()
            dest = "G_PHARMACY" if "pharmacy" in query_lower or "medicine" in query_lower else ("F1_CARDIOLOGY" if "cardio" in query_lower or "heart" in query_lower else ("F2_ORTHOPEDICS" if "ortho" in query_lower or "bone" in query_lower else "G_RECEPTION"))
            return {
                "destination": dest,
                "current_location": context.get("current_location") or "G_ENTRANCE",
                "needs_elevator": "wheelchair" in query_lower or "elevator" in query_lower or "lift" in query_lower,
                "is_urgent": "emergency" in query_lower or "hurry" in query_lower
            }
