"""Authenticated hospital API load users backed by real, pre-provisioned accounts."""

import os
from itertools import count

from locust import HttpUser, between, task


def _required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Set {name} to a real test-account value before starting Locust.")
    return value


class AuthenticatedUser(HttpUser):
    wait_time = between(1, 4)

    def on_start(self) -> None:
        self.client.headers.update({"Authorization": f"Bearer {_required(self.token_env)}"})


class PatientUser(AuthenticatedUser):
    token_env = "LOCUST_PATIENT_TOKEN"
    weight = 3
    _booking_slots = None
    _booking_slot_index = count()

    def on_start(self) -> None:
        super().on_start()
        if PatientUser._booking_slots is None:
            PatientUser._booking_slots = [
                value.strip()
                for value in _required("LOCUST_APPOINTMENT_TIMES").split(",")
                if value.strip()
            ]
        self.booking_time = PatientUser._booking_slots[next(PatientUser._booking_slot_index) % len(PatientUser._booking_slots)]
        self.booking_done = False

    @task(3)
    def check_queue(self) -> None:
        doctor_id = _required("LOCUST_DOCTOR_ID")
        with self.client.get(
            f"/api/v1/queue/status?doctor_id={doctor_id}",
            name="GET /api/v1/queue/status",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"queue status returned {response.status_code}: {response.text[:200]}")
            elif not isinstance(response.json(), (list, dict)):
                response.failure("queue status response was not a JSON collection")

    @task(1)
    def book_appointment(self) -> None:
        if self.booking_done:
            return
        doctor_id = int(_required("LOCUST_DOCTOR_ID"))
        department_id = int(_required("LOCUST_DEPARTMENT_ID"))
        payload = {
            "doctor_id": doctor_id,
            "department_id": department_id,
            "scheduled_time": self.booking_time,
        }
        with self.client.post(
            "/api/v1/appointments",
            json=payload,
            name="POST /api/v1/appointments",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"appointment booking returned {response.status_code}: {response.text[:200]}")
            elif not isinstance(response.json(), dict) or not response.json().get("id"):
                response.failure("appointment response did not contain an id")
            else:
                self.booking_done = True


class StaffUser(AuthenticatedUser):
    token_env = "LOCUST_STAFF_TOKEN"
    weight = 1

    @task(3)
    def view_queue(self) -> None:
        with self.client.get(
            "/api/v1/staff/doctor/queue",
            name="GET /api/v1/staff/doctor/queue",
            catch_response=True,
        ) as response:
            if response.status_code != 200:
                response.failure(f"staff queue returned {response.status_code}: {response.text[:200]}")
            elif not isinstance(response.json(), (list, dict)):
                response.failure("staff queue response was not a JSON collection")

    @task(1)
    def mark_patient_in_room(self) -> None:
        appointment_id = _required("LOCUST_APPOINTMENT_ID")
        with self.client.put(
            f"/api/v1/staff/queue/{appointment_id}/status",
            json={"status": "in_room"},
            name="PUT /api/v1/staff/queue/[appointment_id]/status",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 204):
                response.failure(f"queue status update returned {response.status_code}: {response.text[:200]}")
            elif response.status_code == 200 and not isinstance(response.json(), dict):
                response.failure("queue status update response was not a JSON object")


class EmergencyUser(AuthenticatedUser):
    token_env = "LOCUST_EMERGENCY_TOKEN"
    weight = 1
    wait_time = between(60, 120)

    @task
    def trigger_sos(self) -> None:
        payload = {
            "location": _required("LOCUST_EMERGENCY_LOCATION"),
            "description": "Locust emergency endpoint smoke workload",
        }
        with self.client.post(
            "/api/v1/emergency/sos",
            json=payload,
            name="POST /api/v1/emergency/sos",
            catch_response=True,
        ) as response:
            if response.status_code not in (200, 201):
                response.failure(f"emergency SOS returned {response.status_code}: {response.text[:200]}")
            elif not isinstance(response.json(), dict) or not response.json().get("emergency_id"):
                response.failure("emergency SOS response did not contain an emergency_id")

