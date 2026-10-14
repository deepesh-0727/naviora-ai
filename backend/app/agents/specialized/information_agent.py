from fastapi import HTTPException
from typing import Any


class InformationAgent:
    """Hospital information requires approved records stored in the database."""

    def __init__(self, ollama_url: str | None = None) -> None:
        self.ollama_url = ollama_url

    async def execute(self, user_query: str, context: dict[str, Any]) -> dict[str, Any]:
        raise HTTPException(
            status_code=501,
            detail="Hospital information is unavailable until verified database content is configured.",
        )
