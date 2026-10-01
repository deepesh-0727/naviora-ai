import httpx
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from app.core.config import settings
from app.core.exceptions import AIInferenceError

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    def __init__(self, name: str, system_prompt: str, ollama_url: str = settings.OLLAMA_BASE_URL):
        self.name = name
        self.system_prompt = system_prompt
        self.ollama_url = ollama_url
        self._circuit_open = False
        self._last_failure_time = 0

    @abstractmethod
    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent logic with resilience patterns."""
        pass

    async def call_llm(self, prompt: str, system: Optional[str] = None, model: str = settings.OLLAMA_MODEL) -> str:
        """
        Production-grade LLM call with:
        1. Circuit Breaker
        2. Exponential Backoff Retries
        3. Detailed Telemetry
        """
        if self._circuit_open:
            # Check if we should try to close the circuit (half-open)
            import time
            if time.time() - self._last_failure_time > 60: # 1 minute cooling
                self._circuit_open = False
            else:
                logger.warning(f"Circuit breaker OPEN for agent: {self.name}. Skipping LLM call.")
                raise AIInferenceError(f"AI Service for {self.name} is currently unavailable.")

        payload = {
            "model": model,
            "prompt": prompt,
            "system": system or self.system_prompt,
            "stream": False,
            "options": {"temperature": settings.AI_TEMPERATURE}
        }

        retries = 0
        backoff = 1.0 # initial backoff in seconds

        while retries < settings.AI_MAX_RETRIES:
            try:
                start_time = asyncio.get_event_loop().time()
                async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT) as client:
                    response = await client.post(f"{self.ollama_url}/api/generate", json=payload)
                    latency = (asyncio.get_event_loop().time() - start_time) * 1000

                    if response.status_code == 200:
                        logger.info(f"Agent {self.name} LLM Success | Latency: {latency:.2f}ms | Retry: {retries}")
                        return response.json().get("response", "").strip()

                    logger.error(f"Ollama Error [{response.status_code}] for agent {self.name}")

            except Exception as e:
                logger.error(f"LLM Call Exception in {self.name}: {str(e)} | Retry: {retries}")

            retries += 1
            if retries < settings.AI_MAX_RETRIES:
                wait_time = backoff * (settings.AI_BACKOFF_FACTOR ** (retries - 1))
                logger.info(f"Backing off for {wait_time:.2f}s before retry {retries}...")
                await asyncio.sleep(wait_time)

        # If we reached here, all retries failed
        self._circuit_open = True
        import time
        self._last_failure_time = time.time()
        logger.critical(f"Circuit breaker OPENED for agent: {self.name} after {retries} failed retries.")
        raise AIInferenceError(f"Agent {self.name} failed to process request after multiple attempts.")
