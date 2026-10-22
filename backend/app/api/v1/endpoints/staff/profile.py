from datetime import date, datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.hospital import StaffSchedule
from app.models.operations import StaffAttendance, StaffLeave, StaffShiftSwap
from app.models.user import User

router = APIRouter()
STAFF_ROLES = ["doctor", "nurse", "front_desk", "pharmacy", "facilities", "emergency", "staff"]


class ShiftSwapCreate(BaseModel):
    request: str = Field(min_length=3, max_length=4000)


class LeaveCreate(BaseModel):
    start_date: date
    end_date: date
    reason: str = Field(min_length=3, max_length=4000)


@router.get("/shifts/current")
async def current_shift(
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    result = await db.execute(
        select(StaffSchedule).where(
            StaffSchedule.staff_id == current_user.id,
            StaffSchedule.start_time <= now,
            StaffSchedule.end_time >= now,
        ).order_by(StaffSchedule.start_time.desc()).limit(1)
    )
    schedule = result.scalar_one_or_none()
    if schedule is None:
        return None
    return schedule


@router.post("/shifts/swap", status_code=201)
async def request_shift_swap(
    payload: ShiftSwapCreate,
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    schedule_result = await db.execute(select(StaffSchedule).where(StaffSchedule.staff_id == current_user.id, StaffSchedule.start_time <= now, StaffSchedule.end_time >= now).limit(1))
    schedule = schedule_result.scalar_one_or_none()
    request = StaffShiftSwap(staff_id=current_user.id, schedule_id=schedule.id if schedule else None, request_details=payload.request.strip())
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request


@router.post("/leave", status_code=201)
async def request_leave(
    payload: LeaveCreate,
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    if payload.end_date < payload.start_date or payload.start_date < date.today():
        raise HTTPException(status_code=422, detail="Leave dates must be valid and not in the past.")
    leave = StaffLeave(staff_id=current_user.id, starts_on=payload.start_date, ends_on=payload.end_date, reason=payload.reason.strip())
    db.add(leave)
    await db.commit()
    await db.refresh(leave)
    return leave


@router.get("/attendance")
async def attendance(
    current_user: User = Depends(deps.check_role(STAFF_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(StaffAttendance).where(StaffAttendance.staff_id == current_user.id).order_by(StaffAttendance.recorded_at.desc()))
    return {"items": result.scalars().all()}
