import logging
import json
from typing import Dict, Any
from agents.base_agent import BaseAgent

logger = logging.getLogger(__name__)

class EmergencyAgent(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Emergency Response Coordinator for Naviora AI. "
            "Your job is to triage emergency requests immediately. "
            "Extract: 'emergency_type', 'severity' (1-5), 'location_clues', 'immediate_action_required'."
        )
        super().__init__(name="EmergencyAgent", system_prompt=system_prompt, ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"EmergencyAgent processing: '{user_query}'")

        prompt = (
            f"Triage the following emergency query from a hospital patient or visitor.\n"
            f"Query: \"{user_query}\"\n\n"
            f"SEVERITY SCALE:\n"
            f"1: Immediate Life Threat (Cardiac arrest, massive bleeding, not breathing)\n"
            f"2: Critical (Stroke symptoms, severe chest pain, major trauma)\n"
            f"3: Urgent (Broken bone, high fever, severe allergic reaction)\n"
            f"4: Semi-Urgent (Minor cuts, moderate pain, non-critical flu)\n"
            f"5: Non-Urgent (Information request during emergency, minor discomfort)\n\n"
            f"Output JSON ONLY:\n"
            f"{{\n"
            f"  \"emergency_type\": \"<type>\",\n"
            f"  \"severity\": <1_to_5>,\n"
            f"  \"location_clues\": \"<landmarks_mentioned>\",\n"
            f"  \"immediate_action_required\": \"<short_instruction_for_caller>\"\n"
            f"}}"
        )

        response_text = await self.call_llm(prompt=prompt)

        try:
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            return json.loads(response_text[json_start:json_end])
        except Exception as e:
            logger.error(f"EmergencyAgent failed to parse JSON: {e}")
            return {
                "emergency_type": "unknown",
                "severity": 5,
                "location_clues": None,
                "immediate_action_required": "Please wait for staff arrival."
            }
