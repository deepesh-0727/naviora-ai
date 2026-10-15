from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from redis.asyncio import Redis
from redis.exceptions import RedisError
from pydantic import BaseModel, Field
from sqlalchemy.future import select
from sqlalchemy import update

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import Token, UserRegister, OTPVerification
from app.models.user import User
from app.models.patient import Patient
from app.models.doctor import Doctor
from app.models.security import RefreshToken
from app.services.auth_service import auth_service
from app.services.notification.email_service import email_service
from app.services.otp_service import otp_service
from app.core.rate_limiter import limiter
from app.api import deps

router = APIRouter()


async def _token_claims_for_user(db: AsyncSession, user: User) -> dict[str, int | str | None]:
    """Build authorization context from persisted account/profile rows."""
    claims: dict[str, int | str | None] = {
        "role": user.role,
        "patient_id": None,
        "staff_id": None,
        "department_id": None,
        "ward_id": None,
        "admin_level": None,
    }
    if user.role == "patient":
        result = await db.execute(select(Patient.id).where(Patient.user_id == user.id))
        claims["patient_id"] = result.scalar_one_or_none()
    elif user.role == "doctor":
        result = await db.execute(
            select(Doctor.id, Doctor.department_id).where(Doctor.user_id == user.id)
        )
        doctor = result.one_or_none()
        if doctor:
            claims["staff_id"] = doctor.id
            claims["department_id"] = doctor.department_id
    elif user.role in {"nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff"}:
        claims["staff_id"] = user.id
    return claims


def _refresh_token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


async def _store_refresh_token(db: AsyncSession, user_id: int, token: str) -> None:
    expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES
    )
    db.add(RefreshToken(user_id=user_id, token_hash=_refresh_token_hash(token), expires_at=expires_at))

class UserProfileUpdate(BaseModel):
    phone: str = Field(min_length=1, max_length=20)

@router.get("/me")
async def current_user(current_user=Depends(deps.get_current_active_user)):
    return {
        "id": current_user.id,
        "phone": current_user.phone,
        "email": current_user.email,
        "role": current_user.role,
        "is_verified": current_user.is_verified,
    }

@router.put("/me")
async def update_current_user(
    profile_update: UserProfileUpdate,
    current_user=Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    phone = profile_update.phone.strip()
    if not phone:
        raise HTTPException(status_code=422, detail="Phone number cannot be empty.")
    result = await db.execute(
        select(User).where(User.phone == phone, User.id != current_user.id)
    )
    if result.scalars().first():
        raise HTTPException(status_code=409, detail="This phone number is already in use.")
    current_user.phone = phone
    await db.commit()
    return {"id": current_user.id, "phone": current_user.phone, "email": current_user.email}


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(user_in: UserRegister, db: AsyncSession = Depends(get_db)):
    """
    Register a new patient
    """
    existing_user = await auth_service.get_user_by_phone(db, user_in.phone)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this phone number already exists."
        )
    
    existing_email = await auth_service.get_user_by_email(db, user_in.email)
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists."
        )

    user = await auth_service.register_patient(db, user_in)
    return {"message": "User registered successfully", "phone": user.phone}

@router.post("/login", response_model=Token)
@limiter.limit("5/minute")
async def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login with email or phone number and password
    """
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect email/phone number or password."
        )
    
    token_claims = await _token_claims_for_user(db, user)
    access_token = security.create_access_token(subject=user.id, claims=token_claims)
    refresh_token = security.create_refresh_token(subject=user.id, claims=token_claims)
    await _store_refresh_token(db, user.id, refresh_token)
    await db.commit()
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/otp/generate")
async def generate_otp(phone: str, db: AsyncSession = Depends(get_db)):
    """
    Generate OTP for validation
    """
    normalized_phone = phone.strip()
    user_result = await db.execute(select(User.role).where(User.phone == normalized_phone))
    role = user_result.scalar_one_or_none() or "patient"
    ttl = await otp_service.generate(normalized_phone, role)
    return {"message": "OTP sent successfully", "phone": normalized_phone, "expires_in_seconds": ttl}

@router.post("/otp/verify")
async def verify_otp(verification: OTPVerification):
    """
    Verify OTP for verification
    """
    result = await otp_service.verify(verification.phone.strip(), verification.code)
    if result == "verified":
        return {"message": "OTP verified successfully"}
    if result == "locked":
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many invalid OTP attempts. Try again in 15 minutes.",
        )
    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid OTP verification code.")

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    """
    Refresh JWT token
    """
    try:
        payload = jwt.decode(
            refresh_token, settings.SECRET_KEY, algorithms=[security.ALGORITHM]
        )
        user_id = payload.get("sub")
        token_type = payload.get("type")
        if not user_id or token_type != "refresh":
            raise HTTPException(status_code=400, detail="Invalid refresh token")
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid refresh token")

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    token_result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == _refresh_token_hash(refresh_token),
            RefreshToken.user_id == int(user_id),
            RefreshToken.revoked_at.is_(None),
            RefreshToken.expires_at > now,
        )
    )
    stored_token = token_result.scalar_one_or_none()
    if stored_token is None:
        raise HTTPException(status_code=401, detail="Refresh token is invalid or expired.")

    result = await db.execute(select(User).where(User.id == int(user_id)))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise HTTPException(status_code=401, detail="Account is unavailable.")
    token_claims = await _token_claims_for_user(db, user)
    access_token = security.create_access_token(subject=user.id, claims=token_claims)
    new_refresh_token = security.create_refresh_token(subject=user.id, claims=token_claims)
    stored_token.revoked_at = now
    await _store_refresh_token(db, user.id, new_refresh_token)
    await db.commit()
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout(
    current_user: User = Depends(deps.get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Revoke all outstanding refresh tokens for the authenticated account.
    """
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == current_user.id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=datetime.now(timezone.utc).replace(tzinfo=None))
    )
    await db.commit()
    return {"message": "Logged out successfully"}

@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    """
    Trigger password reset email
    """
    if not settings.EMAIL_API_KEY:
        raise HTTPException(status_code=503, detail="Password reset email is not configured.")

    user = await auth_service.get_user_by_email(db, email)
    if not user:
        return {"message": "If that email is registered, a password reset link has been sent."}
    
    token = secrets.token_urlsafe(32)
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis.set(f"reset_token:{token}", str(user.id), ex=900) # 15 mins
        reset_link = f"com.naviora.ai://reset-password?token={token}"
        if not await email_service.send_password_reset(user.email, reset_link):
            await redis.delete(f"reset_token:{token}")
            raise HTTPException(status_code=503, detail="Unable to send a password reset email right now.")
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="Password reset service is unavailable.") from exc
    finally:
        await redis.aclose()
    return {"message": "If that email is registered, a password reset link has been sent."}

from pydantic import BaseModel
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8, max_length=128)

@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """
    Reset password using token
    """
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        user_id_str = await redis.get(f"reset_token:{request.token}")
        if not user_id_str:
            raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
        
        user_id = int(user_id_str)
        from app.models.user import User
        from sqlalchemy.future import select
        result = await db.execute(select(User).filter(User.id == user_id))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        
        user.password_hash = security.get_password_hash(request.new_password)
        await db.commit()
        await redis.delete(f"reset_token:{request.token}")
    finally:
        await redis.aclose()
    
    return {"message": "Password updated successfully"}
