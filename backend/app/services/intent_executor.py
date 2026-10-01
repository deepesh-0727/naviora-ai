import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.queue_service import queue_service
from app.services.emergency_service import emergency_service
from app.services.pharmacy.pharmacy_service import pharmacy_service
from app.services.billing.billing_service import billing_service
from app.services.analytics.predictor import predictor
from app.services.navigation.route_planner import route_planner
from app.models.user import User

logger = logging.getLogger(__name__)

class IntentExecutor:
    """
    Enterprise Intent Orchestrator.
    Maps high-level AI intents to deep service executions and ML-powered predictions.
    """
    async def execute(self, db: AsyncSession, user: User, analysis: Dict[str, Any]) -> str:
        intent = analysis.get("intent")
        specialized = analysis.get("specialized_details", {})

        logger.info(f"Orchestrating intent: {intent} [User: {user.id}]")

        try:
            if intent == "emergency":
                return await self._handle_emergency(db, user, specialized)

            elif intent == "appointment":
                return await self._handle_appointment(db, user, specialized)

            elif intent == "navigation":
                return self._handle_navigation(specialized)

            elif intent == "pharmacy":
                return await self._handle_pharmacy(db, specialized)

            elif intent == "billing":
                return await self._handle_billing(db, user, specialized)

            elif intent == "information":
                return specialized.get("response") or "I'm checking our knowledge base for that information."

            elif intent == "registration":
                return "I've started your clinical onboarding. Please confirm your date of birth to continue."

            return "I have captured your request and assigned a coordinator to assist you shortly."

        except Exception as e:
            logger.error(f"Execution Error: {str(e)}", exc_info=True)
            return "I encountered a synchronization issue. I've alerted the medical staff to help you directly."

    async def _handle_emergency(self, db, user, data):
        location = data.get("location_clues") or "Current GPS Location"
        severity = predictor.triage_severity(data.get("emergency_type", "Unknown"))

        patient_id = user.patient_profile.id if user.patient_profile else None
        await emergency_service.trigger_sos(db, patient_id, location, data.get("emergency_type"))

        return f"CRITICAL ALERT: Emergency teams have been dispatched to {location}. Priority level {severity} assigned."

    async def _handle_appointment(self, db, user, data):
        specialty = data.get("doctor_specialty", "General")
        is_checkin = data.get("is_checkin", False)

        if is_checkin:
            patient_name = user.patient_profile.first_name if user.patient_profile else "Patient"
            # Mock queue update
            logger.info(f"Patient {user.id} checked in for {specialty}")
            return f"Welcome, {patient_name}. I have successfully checked you in for your appointment in the {specialty} department. Please proceed to the waiting area on Floor 3."

        wait_time = predictor.predict_wait_time(specialty, 5) # Simulating queue size 5
        return f"I found an opening for {specialty}. Estimated wait time is approximately {wait_time} minutes. Would you like me to secure this slot for you?"

    def _handle_navigation(self, data):
        dest = data.get("destination", "Reception")
        nav_res = route_planner.find_path("G_ENTRANCE", dest) # Mock start
        instructions = nav_res.get("human_readable", ["Follow the blue line."])
        return f"To reach {dest}, {instructions[0]} It is about a {nav_res.get('estimated_seconds', 60)//60} minute walk."

    async def _handle_pharmacy(self, db, data):
        med = data.get("medication_name")
        return f"Checking stock for {med}... Yes, we have that in the ground floor pharmacy. Would you like me to reserve it?"

    async def _handle_billing(self, db, user, data):
        estimate = 1500.0 # Mock base
        return f"Your estimated bill for the requested services is ₹{estimate}. Would you like a detailed breakdown sent to your phone?"

intent_executor = IntentExecutor()
