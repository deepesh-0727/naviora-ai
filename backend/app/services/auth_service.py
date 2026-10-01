from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import Optional
import datetime

from app.models.user import User
from app.models.patient import Patient
from app.schemas.auth import UserRegister
from app.core import security
from app.utils.logger import audit_logger

class AuthService:
    async def get_user_by_phone(self, db: AsyncSession, phone: str) -> Optional[User]:
        result = await db.execute(select(User).filter(User.phone == phone))
        return result.scalars().first()

    async def get_user_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(select(User).filter(User.email == email))
        return result.scalars().first()

    async def register_patient(self, db: AsyncSession, user_in: UserRegister) -> User:
        hashed_password = security.get_password_hash(user_in.password)
        db_user = User(
            phone=user_in.phone,
            email=user_in.email,
            password_hash=hashed_password,
            role="patient",
            is_active=True,
            is_verified=False
        )
        db.add(db_user)
        await db.flush()

        db_patient = Patient(
            user_id=db_user.id,
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            date_of_birth=datetime.datetime.combine(
                user_in.date_of_birth or datetime.date.today(),
                datetime.time.min,
            ),
            gender=user_in.gender,
            blood_group=user_in.blood_group,
            allergies=user_in.allergies,
            emergency_contact=user_in.emergency_contact,
            emergency_contact_name=user_in.emergency_contact_name,
            medical_history=user_in.medical_history,
            insurance_provider=user_in.insurance_provider,
            insurance_number=user_in.insurance_number,
        )
        db.add(db_patient)
        await db.commit()
        await db.refresh(db_user)

        audit_logger.log_event(
            action="register_patient",
            user_id=str(db_user.id),
            resource="patient_profile"
        )

        return db_user

    async def authenticate_user(self, db: AsyncSession, phone: str, password: str) -> Optional[User]:
        user = await self.get_user_by_phone(db, phone)
        if not user:
            audit_logger.log_event(action="login_attempt", user_id=phone, resource="auth", status="failed", details={"reason": "phone_not_found"})
            return None
        if not security.verify_password(password, user.password_hash):
            audit_logger.log_event(action="login_attempt", user_id=str(user.id), resource="auth", status="failed", details={"reason": "wrong_password"})
            return None

        audit_logger.log_event(action="login_attempt", user_id=str(user.id), resource="auth", status="success")
        return user

    async def generate_2fa_secret(self, user_id: int) -> str:
        return f"SECRET_FOR_USER_{user_id}_ABC123"

    async def verify_2fa_code(self, user_id: int, code: str) -> bool:
        is_valid = code == "000000"
        audit_logger.log_event(
            action="verify_2fa",
            user_id=str(user_id),
            resource="auth",
            status="success" if is_valid else "failed"
        )
        return is_valid

auth_service = AuthService()
