import logging
import json
import os
import difflib
from typing import Dict, Any, List, Optional
from agents.base_agent import BaseAgent
from app.core.exceptions import AIInferenceError

logger = logging.getLogger(__name__)

class InformationAgent(BaseAgent):
    """
    Enterprise RAG (Retrieval-Augmented Generation) Agent.
    Orchestrates search over hospital knowledge bases and generates human-like clinical responses.
    """
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        system_prompt = (
            "You are the Naviora AI Hospital Information Desk. You speak on behalf of the hospital administration. "
            "You provide accurate, polite, and helpful information using the provided context. "
            "Safety first: If a query sounds like a medical emergency, prioritize suggesting the SOS button."
        )
        super().__init__(name="InformationAgent", system_prompt=system_prompt, ollama_url=ollama_url)

        # Knowledge Base Initialization
        self.kb_path = os.path.join(os.path.dirname(__file__), "../../../backend/app/core/hospital_faq.json")
        self.knowledge_base = self._load_kb()

    def _load_kb(self) -> Dict[str, Any]:
        try:
            if os.path.exists(self.kb_path):
                with open(self.kb_path, 'r') as f:
                    return json.load(f)
            return {}
        except Exception as e:
            logger.error(f"KB Load Error: {e}")
            return {}

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a RAG query:
        1. Search: Find relevant fragments in JSON KB using fuzzy matching.
        2. Augment: Build prompt with found fragments.
        3. Generate: Call LLM for final synthesis.
        """
        logger.info(f"Querying Knowledge Base: '{user_query}'")

        # Step 1: Semantic Search (Simulated with fuzzy matching for zero-cost)
        relevant_context = self._find_relevant_context(user_query)

        # Step 2: Build Prompt
        prompt = (
            f"CLINICAL KNOWLEDGE BASE FRAGMENTS:\n{relevant_context}\n\n"
            f"USER QUERY: \"{user_query}\"\n\n"
            f"SESSION DATA: {json.dumps(context)}\n\n"
            f"GOAL: Synthesize an answer. If fragments are insufficient, state what is missing. "
            f"Output JSON with fields 'response' and 'follow_up_needed'."
        )

        try:
            response_text = await self.call_llm(prompt=prompt)
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            return json.loads(response_text[json_start:json_end])
        except Exception as e:
            logger.error(f"RAG Synthesis Failure: {e}")
            return {"response": "I'm having trouble accessing our info desk. Please ask a nurse for help.", "follow_up_needed": True}

    def _find_relevant_context(self, query: str) -> str:
        """
        Simulates Vector Similarity Search.
        """
        query_words = query.lower().split()
        relevant_fragments = []

        # Search through departments, hours, and policies
        for category, data in self.knowledge_base.items():
            if any(word in str(data).lower() for word in query_words):
                relevant_fragments.append(f"CATEGORY {category.upper()}: {data}")

        return "\n".join(relevant_fragments) if relevant_fragments else "No relevant fragments found."
