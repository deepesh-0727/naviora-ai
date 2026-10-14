import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.emergency import EmergencyCase
from app.services.ws_manager import ws_manager
from app.agents.specialized.emergency_agent import EmergencyAgent

logger = logging.getLogger(__name__)

class EmergencyService:
    def __init__(self):
        self.agent = EmergencyAgent()

    async def trigger_sos(self, db: AsyncSession, patient_id: Optional[int], location: str, description: str = "") -> Dict[str, Any]:
        """
        Trigger an SOS event. Triages the emergency using AI and broadcasts to staff.
        """
        # AI Triage
        triage_data = await self.agent.execute(description or "Immediate assistance needed at " + location, {})

        # Log to DB
        db_emergency = EmergencyCase(
            patient_id=patient_id,
            status="triggered",
            priority=str(triage_data.get("severity", 5)),
            location_desc=location,
            description=description,
            created_at=datetime.utcnow()
        )
        db.add(db_emergency)
        await db.commit()
        await db.refresh(db_emergency)

        event_data = {
            "emergency_id": db_emergency.id,
            "patient_id": db_emergency.patient_id,
            "priority": db_emergency.priority,
            "location": db_emergency.location_desc,
            "description": db_emergency.description,
            "triage": triage_data
        }
        await ws_manager.broadcast_event("emergency", "emergency_new", event_data)
        if db_emergency.patient_id is not None:
            await ws_manager.broadcast_event(f"patient:{db_emergency.patient_id}", "emergency_new", event_data)

        # Global broadcast for extreme critical cases (severity 1 or 2)
        if int(db_emergency.priority) <= 2:
            await ws_manager.broadcast_event("emergency", "global_critical_alert", {
                "emergency_id": db_emergency.id,
                "message": f"CRITICAL: Emergency at {location}. Clear routes for medical team.",
            })

        return {
            "status": "SOS triggered successfully",
            "emergency_id": db_emergency.id,
            "triage": triage_data
        }

    async def assign_staff(self, db: AsyncSession, emergency_id: int, staff_id: int):
        """
        Assign a specific staff member to an emergency case.
        """
        emergency = await db.get(EmergencyCase, emergency_id)
        if not emergency:
            return None
        if emergency.status == "resolved":
            raise ValueError("Resolved emergencies cannot be assigned.")

        assigned_staff = dict(emergency.assigned_staff or {})
        existing_staff_id = assigned_staff.get("primary_staff_id")
        if existing_staff_id is not None and existing_staff_id != staff_id:
            raise ValueError("This emergency is already assigned to another staff member.")
        assigned_staff["primary_staff_id"] = staff_id
        emergency.assigned_staff = assigned_staff
        emergency.status = "staff_assigned"
        await db.commit()
        await db.refresh(emergency)

        event_data = {
            "emergency_id": emergency.id,
            "staff_id": staff_id,
            "location": emergency.location_desc,
        }
        await ws_manager.broadcast_event("emergency", "emergency_ack", event_data)
        if emergency.patient_id is not None:
            await ws_manager.broadcast_event(f"patient:{emergency.patient_id}", "emergency_ack", event_data)
        return emergency

emergency_service = EmergencyService()
