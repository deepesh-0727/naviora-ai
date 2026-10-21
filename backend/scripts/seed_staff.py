"""Prepare the initial demo admin and doctor accounts.

Set NAVIORA_SEED_ADMIN_PASSWORD and NAVIORA_SEED_DOCTOR_PASSWORD before running.
Remote databases require the explicit --allow-remote flag. Existing accounts are
left unchanged so rerunning this script does not reset credentials.
"""
import argparse
import asyncio
import os
from urllib.parse import urlparse

from sqlalchemy import select

from app.core.config import settings
from app.core.security import get_password_hash
from app.db.base import Base  # noqa: F401 - imports all mapped models
from app.db.session import SessionLocal
from app.models.doctor import Department, Doctor
from app.models.user import User


async def seed() -> None:
    admin_password = os.getenv("NAVIORA_SEED_ADMIN_PASSWORD", "")
    doctor_password = os.getenv("NAVIORA_SEED_DOCTOR_PASSWORD", "")
    if len(admin_password) < 12 or len(doctor_password) < 12:
        raise SystemExit("Set both seed password environment variables to passwords of at least 12 characters.")

    async with SessionLocal() as db:
        department_id = os.getenv("NAVIORA_SEED_DOCTOR_DEPARTMENT_ID")
        if department_id:
            department = await db.get(Department, int(department_id))
        else:
            department = await db.scalar(select(Department).order_by(Department.id).limit(1))
        if department is None:
            raise SystemExit("No department exists. Create one first or set NAVIORA_SEED_DOCTOR_DEPARTMENT_ID.")

        accounts = [
            ("admin@naviora.ai", os.getenv("NAVIORA_SEED_ADMIN_PHONE", "9000000001"), "admin", "Demo", "Admin", admin_password),
            ("doctor@naviora.ai", os.getenv("NAVIORA_SEED_DOCTOR_PHONE", "9000000002"), "doctor", "Demo", "Doctor", doctor_password),
        ]
        for email, phone, role, first_name, last_name, password in accounts:
            existing = await db.scalar(select(User).where(User.email == email))
            if existing is not None:
                if existing.role != role:
                    raise SystemExit(f"{email} already exists with role '{existing.role}', expected '{role}'. No changes were made.")
                print(f"Keeping existing {role} account: {email}")
                continue

            phone_owner = await db.scalar(select(User.id).where(User.phone == phone))
            if phone_owner is not None:
                raise SystemExit(f"Phone {phone} is already in use. Set a unique phone environment variable.")
            user = User(
                email=email,
                phone=phone,
                password_hash=get_password_hash(password),
                role=role,
                first_name=first_name,
                last_name=last_name,
                is_verified=True,
                is_active=True,
            )
            db.add(user)
            await db.flush()
            if role == "doctor":
                db.add(Doctor(
                    user_id=user.id,
                    first_name=first_name,
                    last_name=last_name,
                    specialization=os.getenv("NAVIORA_SEED_DOCTOR_SPECIALIZATION", "General Medicine"),
                    department_id=department.id,
                    license_number=os.getenv("NAVIORA_SEED_DOCTOR_LICENSE", "NAVIORA-DEMO-DOCTOR-001"),
                    years_of_experience=0,
                ))
            print(f"Prepared {role} account: {email}")

        await db.commit()
        print("Seeding complete. Passwords were read from environment variables and were not printed.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-remote", action="store_true", help="explicitly allow writes to a non-local database")
    args = parser.parse_args()
    parsed = urlparse(settings.DATABASE_URL)
    local_hosts = {"", "localhost", "127.0.0.1", "::1"}
    if parsed.hostname not in local_hosts and not args.allow_remote:
        raise SystemExit("Refusing to write to a remote database. Review the target and rerun with --allow-remote if intended.")
    asyncio.run(seed())


if __name__ == "__main__":
    main()
