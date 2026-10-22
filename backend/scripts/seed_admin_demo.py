"""Add idempotent billing, analytics, and hospital profile demo records.

Remote database writes are blocked by default. Review the target database and pass
--allow-remote only when seeding a remote pilot database is intended.
"""
import argparse
import asyncio
from datetime import datetime
from decimal import Decimal
from urllib.parse import urlparse

from sqlalchemy import select

from app.core.config import settings
from app.db.base import Base  # noqa: F401 - register all mapped models
from app.db.session import SessionLocal
from app.models.billing import Billing
from app.models.hospital import AuditLog
from app.models.operations import SystemSetting
from app.models.patient import Patient
from app.models.user import User

DEMO_MARKER = "seed_admin_demo:v1"


async def seed() -> None:
    async with SessionLocal() as db:
        admin = await db.scalar(select(User).where(User.role.in_(["admin", "super_admin"])).order_by(User.id).limit(1))
        if admin is None:
            raise SystemExit("Create an admin account before seeding demo settings and analytics records.")

        profile = await db.scalar(select(SystemSetting).where(SystemSetting.key == "hospital_profile"))
        if profile is None:
            db.add(SystemSetting(
                key="hospital_profile",
                value={"hospital_name": "Naviora General", "contact_phone": "", "emergency_line": ""},
                updated_by_id=admin.id,
            ))
            print("Added default hospital profile settings.")
        else:
            print("Kept existing hospital profile settings.")

        patient = await db.scalar(select(Patient).order_by(Patient.id).limit(1))
        if patient is None:
            raise SystemExit("A patient is required before demo invoices can be added.")

        for invoice_number, amount, invoice_status in (
            ("DEMO-INV-001", Decimal("1250.00"), "pending"),
            ("DEMO-INV-002", Decimal("850.00"), "cancelled"),
        ):
            existing = await db.scalar(select(Billing.id).where(Billing.invoice_number == invoice_number))
            if existing is None:
                db.add(Billing(
                    patient_id=patient.id,
                    amount=amount,
                    status=invoice_status,
                    invoice_number=invoice_number,
                    items=[{"name": "Demo hospital service", "quantity": 1, "price": str(amount)}],
                ))
                print(f"Added demo invoice {invoice_number}.")
            else:
                print(f"Kept existing demo invoice {invoice_number}.")

        for action in ("patient_registered", "appointment_booked"):
            exists = await db.scalar(select(AuditLog.id).where(
                AuditLog.action == action,
                AuditLog.resource == "demo_analytics",
                AuditLog.details == DEMO_MARKER,
            ))
            if exists is None:
                db.add(AuditLog(
                    user_id=admin.id,
                    action=action,
                    resource="demo_analytics",
                    method="SEED",
                    details=DEMO_MARKER,
                    status="demo",
                    created_at=datetime.utcnow(),
                ))
                print(f"Added demo analytics event {action}.")
            else:
                print(f"Kept existing demo analytics event {action}.")

        await db.commit()
        print("Demo data seeding complete.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-remote", action="store_true", help="allow writes to the configured remote database")
    args = parser.parse_args()
    parsed = urlparse(settings.DATABASE_URL)
    if parsed.hostname not in {"", "localhost", "127.0.0.1", "::1"} and not args.allow_remote:
        raise SystemExit("Refusing to write demo data to a remote database without --allow-remote.")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
