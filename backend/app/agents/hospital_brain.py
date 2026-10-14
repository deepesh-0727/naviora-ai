import logging
import json
from typing import Dict, Any
from .base_agent import BaseAgent
from .specialized.appointment_agent import AppointmentAgent
from .specialized.emergency_agent import EmergencyAgent
from .specialized.navigation_agent import NavigationAgent
from .specialized.pharmacy_agent import PharmacyAgent
from .specialized.information_agent import InformationAgent
from .specialized.registration_agent import RegistrationAgent
from .specialized.billing_agent import BillingAgent
from .specialized.facility_management_agent import FacilityManagementAgent
from .specialized.doctor_assistance_agent import DoctorAssistanceAgent
from app.core.config import settings

logger = logging.getLogger(__name__)

class HospitalBrain(BaseAgent):
    def __init__(self, ollama_url: str = settings.OLLAMA_BASE_URL):
        system_prompt = (
            "You are the HospitalBrain Master Agent for Naviora AI. "
            "Your job is to analyze the patient request, detect intent, extract relevant entities, "
            "and output a clean JSON with fields: 'intent', 'confidence', 'entities' (a dictionary)."
        )
        super().__init__(name="HospitalBrain", system_prompt=system_prompt, ollama_url=ollama_url)

        # Initialize specialized agents
        self.appointment_agent = AppointmentAgent(ollama_url=ollama_url)
        self.emergency_agent = EmergencyAgent(ollama_url=ollama_url)
        self.navigation_agent = NavigationAgent(ollama_url=ollama_url)
        self.pharmacy_agent = PharmacyAgent(ollama_url=ollama_url)
        self.information_agent = InformationAgent(ollama_url=ollama_url)
        self.registration_agent = RegistrationAgent(ollama_url=ollama_url)
        self.billing_agent = BillingAgent(ollama_url=ollama_url)
        self.facility_management_agent = FacilityManagementAgent(ollama_url=ollama_url)
        self.doctor_assistance_agent = DoctorAssistanceAgent(ollama_url=ollama_url)

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info("HospitalBrain processing an authenticated voice request")
        cache_scope = str(context.get("user_id") or "anonymous")
        
        # Step 0: Check Cache for cached intent classification
        from app.services.cache_service import cache_service
        cached_res = await cache_service.get_cached_intent(user_query, scope=cache_scope)
        if cached_res:
            base_analysis = cached_res
        else:
            # Step 1: Intent Classification via LLM
            prompt = (
                f"Classify the following query from a hospital visitor or patient.\n"
                f"Query: \"{user_query}\"\n\n"
                f"Map the query to one of the following intents:\n"
                f"- 'appointment' (booking, scheduling, canceling, availability, check-in, arriving at clinic)\n"
                f"- 'emergency' (critical condition, accident, cardiac arrest, immediate distress)\n"
                f"- 'navigation' (seeking directions, departments, lifts, parking, toilets)\n"
                f"- 'pharmacy' (medication availability, dosage, refills, pharmacy hours)\n"
                f"- 'information' (visiting hours, insurance details, FAQs)\n"
                f"- 'registration' (registering new patients, update profile)\n"
                f"- 'billing' (invoices, payments, insurance claims, bill estimation)\n"
                f"- 'identity' (login, otp code)\n\n"
                f"Output JSON ONLY in the following format:\n"
                f"{{\n"
                f"  \"intent\": \"<intent_name>\",\n"
                f"  \"confidence\": <float_0_to_1>,\n"
                f"  \"entities\": {{\n"
                f"    \"doctor\": \"<doctor_name_if_present>\",\n"
                f"    \"department\": \"<department_if_present>\",\n"
                f"    \"time\": \"<time_or_date_if_present>\"\n"
                f"  }}\n"
                f"}}"
            )

            try:
                response_text = await self.call_llm(prompt=prompt)
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                if json_start != -1 and json_end != -1:
                    base_analysis = json.loads(response_text[json_start:json_end])
                else:
                    base_analysis = json.loads(response_text)
                if not isinstance(base_analysis, dict):
                    raise ValueError("Classifier result must be a JSON object")
                confidence = base_analysis.get("confidence")
                if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
                    raise ValueError("Classifier confidence is invalid")
            except Exception as e:
                logger.warning("LLM classifier unavailable; using conservative rule classifier: %s", type(e).__name__)
                base_analysis = self._rule_classify(user_query)

            # Store result in Redis cache
            await cache_service.set_cached_intent(user_query, base_analysis, ttl=3600, scope=cache_scope)

        intent = base_analysis.get("intent")
        logger.info(f"HospitalBrain detected intent: {intent}")

        if float(base_analysis.get("confidence", 0)) < 0.6:
            return {**base_analysis, "specialized_details": {}, "needs_clarification": True}

        # Step 2: Delegation to Specialized Agents
        specialized_data = {}
        if intent == "appointment":
            specialized_data = await self.appointment_agent.execute(user_query, context)
        elif intent == "emergency":
            specialized_data = await self.emergency_agent.execute(user_query, context)
        elif intent == "navigation":
            specialized_data = await self.navigation_agent.execute(user_query, context)
        elif intent == "pharmacy":
            specialized_data = await self.pharmacy_agent.execute(user_query, context)
        elif intent == "information":
            specialized_data = await self.information_agent.execute(user_query, context)
        elif intent == "registration":
            specialized_data = await self.registration_agent.execute(user_query, context)
        elif intent == "billing":
            specialized_data = await self.billing_agent.execute(user_query, context)
        elif intent == "facility_management":
            specialized_data = await self.facility_management_agent.execute(user_query, context)
        elif intent == "doctor_assistance":
            specialized_data = await self.doctor_assistance_agent.execute(user_query, context)

        # Merge results
        final_response = {
            **base_analysis,
            "specialized_details": specialized_data
        }

        return final_response

    @staticmethod
    def _rule_classify(query: str) -> Dict[str, Any]:
        """Conservative offline intent classifier; low-confidence text is never actioned."""
        normalized = query.casefold()
        patterns = {
            "emergency": ("emergency", "chest pain", "can't breathe", "cannot breathe", "bleeding", "accident", "unconscious", "stroke"),
            "appointment": ("appointment", "book a doctor", "schedule a visit", "reschedule"),
            "navigation": ("directions", "where is", "how do i get", "navigate to"),
            "pharmacy": ("pharmacy", "medicine", "prescription", "refill"),
            "registration": ("register", "sign up", "update my profile"),
            "billing": ("bill", "invoice", "payment", "insurance claim"),
            "information": ("visiting hours", "hospital hours", "contact information"),
            "facility_management": ("broken bed", "equipment issue", "maintenance request"),
            "doctor_assistance": ("clinical summary", "patient history", "doctor assistance"),
        }
        matches = [intent for intent, phrases in patterns.items() if any(phrase in normalized for phrase in phrases)]
        if len(matches) == 1:
            confidence = 0.9 if matches[0] == "emergency" else 0.72
            return {"intent": matches[0], "confidence": confidence, "entities": {}}
        return {"intent": None, "confidence": 0.0, "entities": {}}
