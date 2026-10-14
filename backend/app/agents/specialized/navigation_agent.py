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
        logger.info("NavigationAgent processing a request")

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
            logger.warning("Navigation extraction unavailable: %s", type(e).__name__)
            return {
                "destination": None,
                "current_location": context.get("current_location"),
                "needs_elevator": None,
                "is_urgent": None,
            }
