import logging
import json
from typing import Dict, Any
from agents.base_agent import BaseAgent

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

        response_text = await self.call_llm(prompt=prompt)

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            return json.loads(response_text[json_start:json_end])
        except Exception as e:
            logger.error(f"NavigationAgent failed to parse JSON: {e}")
            return {
                "destination": None,
                "current_location": None,
                "needs_elevator": False,
                "is_urgent": False
            }
