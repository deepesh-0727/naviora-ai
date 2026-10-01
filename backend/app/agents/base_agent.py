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

    async def _call_ollama(self, prompt: str, system: Optional[str] = None, model: str = settings.OLLAMA_MODEL) -> str:
        payload = {
            "model": model,
            "prompt": prompt,
            "system": system or self.system_prompt,
            "stream": False,
            "options": {"temperature": settings.AI_TEMPERATURE}
        }
        async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT) as client:
            response = await client.post(f"{self.ollama_url}/api/generate", json=payload)
            if response.status_code == 200:
                return response.json().get("response", "").strip()
            raise AIInferenceError(f"Ollama API returned status code {response.status_code}")

    async def _call_openai(self, prompt: str, system: Optional[str] = None) -> str:
        if not settings.OPENAI_API_KEY:
            raise AIInferenceError("OpenAI API key not configured")
        
        headers = {
            "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [
                {"role": "system", "content": system or self.system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": settings.AI_TEMPERATURE
        }
        async with httpx.AsyncClient(timeout=settings.AI_REQUEST_TIMEOUT) as client:
            response = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            raise AIInferenceError(f"OpenAI API returned status code {response.status_code}")

    async def call_llm(self, prompt: str, system: Optional[str] = None, model: str = settings.OLLAMA_MODEL) -> str:
        """
        Production-grade LLM call with:
        1. Multi-Provider Fallback (Primary: Ollama, Fallback: OpenAI)
        2. Circuit Breaker
        3. Exponential Backoff Retries
        """
        import time
        if self._circuit_open:
            if time.time() - self._last_failure_time > 60:  # 1 minute cooling
                self._circuit_open = False
                logger.info(f"Circuit breaker HALF-OPEN for agent: {self.name}")
            else:
                logger.warning(f"Circuit breaker OPEN for agent: {self.name}. Skipping LLM call.")
                raise AIInferenceError(f"AI Service for {self.name} is currently unavailable.")

        retries = 0
        backoff = 1.0

        # Try Primary Provider (Ollama) with retries
        while retries < settings.AI_MAX_RETRIES:
            try:
                start_time = asyncio.get_event_loop().time()
                result = await self._call_ollama(prompt, system, model)
                latency = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.info(f"Agent {self.name} [Ollama] Success | Latency: {latency:.2f}ms | Retry: {retries}")
                return result
            except Exception as e:
                logger.warning(f"Agent {self.name} Ollama call failed: {e} | Retry: {retries}")

            retries += 1
            if retries < settings.AI_MAX_RETRIES:
                wait_time = backoff * (settings.AI_BACKOFF_FACTOR ** (retries - 1))
                await asyncio.sleep(wait_time)

        # Primary failed, attempt Fallback 1 (OpenAI) if configured
        if settings.OPENAI_API_KEY:
            try:
                logger.info(f"Agent {self.name} attempting fallback to OpenAI...")
                start_time = asyncio.get_event_loop().time()
                result = await self._call_openai(prompt, system)
                latency = (asyncio.get_event_loop().time() - start_time) * 1000
                logger.info(f"Agent {self.name} [OpenAI] Success | Latency: {latency:.2f}ms")
                return result
            except Exception as e:
                logger.error(f"Agent {self.name} OpenAI fallback failed: {e}")

        # Open circuit breaker if both primary and fallback failed
        self._circuit_open = True
        self._last_failure_time = time.time()
        logger.critical(f"Circuit breaker OPENED for agent: {self.name} after all retries and fallbacks failed.")
        raise AIInferenceError(f"Agent {self.name} failed to process request after primary and fallback attempts.")

