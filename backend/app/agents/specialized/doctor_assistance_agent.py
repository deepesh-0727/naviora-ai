from typing import Any

from fastapi import HTTPException

from app.agents.base_agent import BaseAgent
from app.core.config import settings


class DoctorAssistanceAgent(BaseAgent):
    def __init__(self, ollama_url: str = settings.OLLAMA_BASE_URL) -> None:
        super().__init__("DoctorAssistanceAgent", "Extract a doctor assistance request as JSON. Never invent patient facts.", ollama_url)

    async def execute(self, user_query: str, context: dict[str, Any]) -> dict[str, Any]:
        if not context.get("user_id"):
            raise HTTPException(status_code=403, detail="An authenticated clinician is required.")
        try:
            response = await self.call_llm(
                f"Extract request_type and patient_identifier from this query. Return JSON only. Query: {user_query}"
            )
            import json
            value = json.loads(response[response.find("{"):response.rfind("}") + 1])
            return value if isinstance(value, dict) else {}
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Doctor assistance extraction is unavailable.") from exc
