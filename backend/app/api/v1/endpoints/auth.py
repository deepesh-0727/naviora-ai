from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
import jwt
import secrets
import hashlib
from redis.asyncio import Redis
from redis.exceptions import RedisError
from pydantic import BaseModel, Field
from sqlalchemy.future import select

from app.core import security
from app.core.config import settings
from app.db.session import get_db
from app.schemas.auth import Token, UserRegister, OTPVerification
from app.models.user import User
from app.services.auth_service import auth_service
from app.services.notification.sms_service import sms_service
from app.api import deps

router = APIRouter()
OTP_TTL_SECONDS = 300

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


def _otp_key(phone: str) -> str:
    phone_hash = hashlib.sha256(phone.encode("utf-8")).hexdigest()
    return f"naviora:otp:{phone_hash}"

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
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    """
    Login with phone and password
    """
    user = await auth_service.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Incorrect phone number or password."
        )
    
    access_token = security.create_access_token(subject=user.id)
    refresh_token = security.create_refresh_token(subject=user.id)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }

@router.post("/otp/generate")
async def generate_otp(phone: str):
    """
    Generate OTP for validation
    """
    code = f"{secrets.randbelow(1_000_000):06d}"
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis.set(_otp_key(phone), code, ex=OTP_TTL_SECONDS)
        delivered = await sms_service.send_otp(phone, code)
        if not delivered:
            await redis.delete(_otp_key(phone))
            raise HTTPException(status_code=503, detail="Unable to send OTP.")
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="OTP service is unavailable.") from exc
    finally:
        await redis.aclose()
    return {"message": "OTP sent successfully", "phone": phone, "expires_in_seconds": 300}

@router.post("/otp/verify")
async def verify_otp(verification: OTPVerification):
    """
    Verify OTP for verification
    """
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        stored = await redis.get(_otp_key(verification.phone))
        if stored and secrets.compare_digest(verification.code, stored):
            await redis.delete(_otp_key(verification.phone))
            return {"message": "OTP verified successfully"}
    except RedisError as exc:
        raise HTTPException(status_code=503, detail="OTP service is unavailable.") from exc
    finally:
        await redis.aclose()
    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid OTP verification code."
    )

@router.post("/refresh", response_model=Token)
async def refresh_token(refresh_token: str):
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

    access_token = security.create_access_token(subject=user_id)
    new_refresh_token = security.create_refresh_token(subject=user_id)
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@router.post("/logout")
async def logout():
    """
    Logout user (client-side token deletion, server-side blacklisting stub)
    """
    return {"message": "Logged out successfully"}

@router.post("/forgot-password")
async def forgot_password(email: str, db: AsyncSession = Depends(get_db)):
    """
    Trigger password reset email
    """
    user = await auth_service.get_user_by_email(db, email)
    if not user:
        return {"message": "If that email is registered, a password reset link has been sent."}
    
    token = secrets.token_urlsafe(32)
    redis = Redis.from_url(settings.REDIS_URL, decode_responses=True)
    try:
        await redis.set(f"reset_token:{token}", str(user.id), ex=900) # 15 mins
        # Simulating email sending via SendGrid
        logger.info(f"Password reset link: https://naviora.ai/reset-password?token={token}")
    finally:
        await redis.aclose()
    return {"message": "If that email is registered, a password reset link has been sent."}

from pydantic import BaseModel
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str

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
