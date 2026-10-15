from datetime import datetime, timezone
from difflib import get_close_matches
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.doctor import Department, Doctor
from app.models.patient import Patient
from app.models.user import User
from app.services.availability_service import database_datetime, get_available_slots
from app.services.emergency_service import emergency_service


class IntentExecutor:
    """Execute only intents backed by a persisted service operation."""

    async def execute(self, db: AsyncSession, user: User, analysis: dict[str, Any]) -> str | dict[str, Any]:
        intent = analysis.get("intent")
        if analysis.get("needs_clarification") or float(analysis.get("confidence") or 0) < 0.6:
            return "I could not identify the request with enough confidence. Please rephrase or provide more details."
        details = analysis.get("specialized_details") or {}
        if intent == "appointment":
            return await self._prepare_appointment(db, user, analysis, details)
        if intent != "emergency":
            raise HTTPException(
                status_code=501,
                detail=f"The {intent or 'requested'} voice action is not available yet.",
            )

        patient_result = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
        patient_id = patient_result.scalar_one_or_none()
        location = details.get("location") or details.get("location_clues")
        description = details.get("emergency_type") or details.get("description")
        if patient_id is None:
            raise HTTPException(status_code=403, detail="Emergency voice requests require a patient account.")
        if not isinstance(location, str) or not location.strip():
            return "Please share your current location so I can submit the emergency request."

        result = await emergency_service.trigger_sos(
            db,
            patient_id,
            location.strip(),
            description.strip() if isinstance(description, str) else "",
        )
        return f"Emergency request {result['emergency_id']} was recorded."

    async def _prepare_appointment(
        self,
        db: AsyncSession,
        user: User,
        analysis: dict[str, Any],
        details: dict[str, Any],
    ) -> dict[str, Any]:
        """Resolve a proposed appointment without persisting it; confirmation is a later step."""
        if user.role != "patient":
            raise HTTPException(status_code=403, detail="Appointment voice requests require a patient account.")

        patient_id = await db.scalar(select(Patient.id).where(Patient.user_id == user.id))
        if patient_id is None:
            raise HTTPException(status_code=404, detail="Patient profile not found.")

        entities = analysis.get("entities")
        entities = entities if isinstance(entities, dict) else {}
        partial_intent = {
            "doctor_name": self._first_text(
                entities.get("doctor_name"), entities.get("doctor"),
                details.get("doctor_name"), details.get("doctor"),
            ),
            "date": self._first_text(entities.get("date"), details.get("date")),
            "time": self._first_text(entities.get("time"), details.get("time")),
            "preferred_time": self._first_text(details.get("preferred_time")),
            "department_name": self._first_text(
                entities.get("department_name"), entities.get("department"),
                details.get("department_name"), details.get("department"),
            ),
            "symptoms": self._first_text(entities.get("symptoms"), details.get("symptoms")),
        }
        specialty = self._first_text(details.get("doctor_specialty"), entities.get("specialty"))

        doctor_query = await db.execute(
            select(Doctor, Department)
            .join(Department, Department.id == Doctor.department_id)
            .join(User, User.id == Doctor.user_id)
            .where(Doctor.is_available.is_(True), User.is_active.is_(True))
        )
        doctor_rows = doctor_query.all()
        department_name = partial_intent["department_name"]
        if department_name:
            department_matches = [
                row for row in doctor_rows
                if row[1].name.casefold() == department_name.casefold()
            ]
            if not department_matches:
                names = self._candidate_names(doctor_rows[:5])
                question = f"I couldn't find a department named '{department_name}'. Which department did you mean?"
                return self._clarification(question, partial_intent, candidates=names)
            doctor_rows = department_matches

        doctor_name = partial_intent["doctor_name"]
        if not doctor_name and specialty:
            specialty_rows = [
                row for row in doctor_rows
                if specialty.casefold() in row[0].specialization.casefold()
            ]
            names = self._candidate_names(specialty_rows[:5])
            question = f"Which doctor would you like to see in {department_name or specialty}?"
            return self._clarification(question, partial_intent, candidates=names)
        if not doctor_name:
            return self._clarification("Which doctor would you like to see?", partial_intent)

        normalized_query = self._normalize_name(doctor_name)
        exact_matches = [
            row for row in doctor_rows
            if normalized_query in {
                self._normalize_name(f"{row[0].first_name} {row[0].last_name}"),
                self._normalize_name(row[0].last_name),
            }
        ]
        matched_rows = exact_matches or [
            row for row in doctor_rows
            if normalized_query in self._normalize_name(f"{row[0].first_name} {row[0].last_name}")
        ]
        if not matched_rows:
            doctor_name_pairs = [
                (row, self._normalize_name(f"Dr. {row[0].first_name} {row[0].last_name}"))
                for row in doctor_rows
            ]
            closest_names = get_close_matches(
                normalized_query,
                [normalized for _row, normalized in doctor_name_pairs],
                n=3,
                cutoff=0.45,
            )
            closest = [
                self._doctor_label(*row)
                for row, normalized in doctor_name_pairs
                if normalized in closest_names
            ]
            suggestion = f" Did you mean {', '.join(closest)}?" if closest else " Please check the name and try again."
            question = f"I couldn't find a doctor named '{doctor_name}'.{suggestion}"
            return self._clarification(question, partial_intent, candidates=closest)
        if len(matched_rows) > 1:
            candidates = self._candidate_names(matched_rows)
            question = f"I found multiple doctors matching '{doctor_name}'. Which one would you like?"
            return self._clarification(question, partial_intent, candidates=candidates)

        doctor, department = matched_rows[0]
        requested_slot = self._requested_slot(partial_intent)
        if requested_slot is None:
            return self._clarification(
                f"When would you like to see Dr. {doctor.first_name} {doctor.last_name}?",
                partial_intent,
                candidates=[self._doctor_label(doctor, department)],
            )

        requested_slot = database_datetime(requested_slot)
        now_utc = datetime.now(timezone.utc).replace(tzinfo=None)
        if requested_slot <= now_utc:
            return self._clarification("That date and time has already passed. When would you like to see the doctor?", partial_intent)

        slots = [database_datetime(datetime.fromisoformat(slot)) for slot in await get_available_slots(db, doctor, requested_slot.date())]
        if requested_slot not in slots:
            alternatives = [slot.isoformat() for slot in slots[:3]]
            if alternatives:
                question = f"That slot is taken or unavailable. Here are the next available times: {', '.join(alternatives)}. Which works for you?"
            else:
                question = f"Dr. {doctor.first_name} {doctor.last_name} has no available times on {requested_slot.date().isoformat()}. Which other date works for you?"
            return self._clarification(question, partial_intent, alternatives=alternatives)

        proposal = {
            "patient_id": patient_id,
            "doctor_id": doctor.id,
            "doctor_name": f"Dr. {doctor.first_name} {doctor.last_name}",
            "department_id": department.id,
            "department_name": department.name,
            "scheduled_time": requested_slot.isoformat(),
            "symptoms": partial_intent["symptoms"],
        }
        return {
            "needs_clarification": False,
            "needs_confirmation": True,
            "clarification_question": None,
            "partial_intent": partial_intent,
            "booking_proposal": proposal,
            "response_text": (
                f"I found {proposal['doctor_name']} in {department.name}. "
                f"{requested_slot.strftime('%B %d at %I:%M %p').replace(' 0', ' ').lstrip('0')} is available. "
                "I will ask you to confirm before anything is booked."
            ),
        }

    @staticmethod
    def _first_text(*values: Any) -> str | None:
        for value in values:
            if isinstance(value, str) and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _normalize_name(value: str) -> str:
        normalized = " ".join(value.casefold().replace(".", " ").split())
        return normalized.removeprefix("dr ").strip()

    @staticmethod
    def _doctor_label(doctor: Doctor, department: Department) -> str:
        return f"Dr. {doctor.first_name} {doctor.last_name} — {department.name}"

    @classmethod
    def _candidate_names(cls, rows: list[tuple[Doctor, Department]]) -> list[str]:
        return [cls._doctor_label(doctor, department) for doctor, department in rows]

    @staticmethod
    def _requested_slot(partial_intent: dict[str, str | None]) -> datetime | None:
        preferred = partial_intent.get("preferred_time")
        if preferred:
            try:
                return datetime.fromisoformat(preferred.replace("Z", "+00:00"))
            except ValueError:
                pass

        requested_date = partial_intent.get("date")
        requested_time = partial_intent.get("time")
        if requested_date and requested_time:
            try:
                return datetime.fromisoformat(f"{requested_date}T{requested_time}")
            except ValueError:
                pass
        return None

    @staticmethod
    def _clarification(
        question: str,
        partial_intent: dict[str, str | None],
        *,
        candidates: list[str] | None = None,
        alternatives: list[str] | None = None,
    ) -> dict[str, Any]:
        result: dict[str, Any] = {
            "needs_clarification": True,
            "needs_confirmation": False,
            "clarification_question": question,
            "partial_intent": partial_intent,
            "response_text": question,
        }
        if candidates is not None:
            result["candidates"] = candidates
        if alternatives is not None:
            result["alternatives"] = alternatives
        return result


intent_executor = IntentExecutor()
