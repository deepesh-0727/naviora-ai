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

logger = logging.getLogger(__name__)

class HospitalBrain(BaseAgent):
    def __init__(self, ollama_url: str = "http://localhost:11434"):
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

    async def execute(self, user_query: str, context: Dict[str, Any]) -> Dict[str, Any]:
        logger.info(f"HospitalBrain processing query: '{user_query}'")
        
        # Step 0: Check Cache for cached intent classification
        from app.services.cache_service import cache_service
        cached_res = await cache_service.get_cached_intent(user_query)
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
            except Exception as e:
                logger.warning(f"HospitalBrain using fallback classifier: {e}")
                base_analysis = self._fallback_classifier(user_query)

            # Store result in Redis cache
            await cache_service.set_cached_intent(user_query, base_analysis)

        intent = base_analysis.get("intent")
        logger.info(f"HospitalBrain detected intent: {intent}")

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

        # Merge results
        final_response = {
            **base_analysis,
            "specialized_details": specialized_data
        }

        return final_response

    def _fallback_classifier(self, query: str) -> Dict[str, Any]:
        query_lower = query.lower()
        
        # 1. Emergency (highest priority in triage)
        if any(w in query_lower for w in ["emergency", "critical", "pain", "accident", "ambulance", "die", "attack", "unconscious", "stroke", "bleed", "cardiac", "urgent", "help"]):
            return {"intent": "emergency", "confidence": 0.9, "entities": {}}
        
        # 2. Appointment Booking & Doctor Scheduling
        elif any(w in query_lower for w in ["book", "appointment", "doctor", "schedule", "appoint", "slot", "consult", "check in", "i am here", "arrived"]):
            return {"intent": "appointment", "confidence": 0.85, "entities": {}}
        
        # 3. Pharmacy & Medications
        elif any(w in query_lower for w in ["pharmacy", "medicine", "medication", "pill", "tablet", "dosage", "prescription", "paracetamol", "amoxicillin", "stock", "refill"]):
            return {"intent": "pharmacy", "confidence": 0.85, "entities": {}}
        
        # 4. Navigation & Wayfinding
        elif any(w in query_lower for w in ["where is", "navigate", "directions", "how to get", "route", "way to", "location of", "floor map", "find"]):
            return {"intent": "navigation", "confidence": 0.85, "entities": {}}
        
        # 5. Billing & Invoices
        elif any(w in query_lower for w in ["pay", "bill", "invoice", "cost", "price", "fee", "estimate", "charges", "insurance claim"]):
            return {"intent": "billing", "confidence": 0.85, "entities": {}}
        
        # 6. Patient Registration
        elif any(w in query_lower for w in ["register", "sign up", "onboard", "new patient", "create account", "profile"]):
            return {"intent": "registration", "confidence": 0.85, "entities": {}}
        
        # 7. General Information & FAQ
        elif any(w in query_lower for w in ["visiting", "hours", "timing", "policy", "faq", "info", "information", "rules"]):
            return {"intent": "information", "confidence": 0.85, "entities": {}}
        
        else:
            return {"intent": "information", "confidence": 0.6, "entities": {}}
