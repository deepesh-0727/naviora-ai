from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.bed import Bed
from app.models.hospital import StaffSchedule
from app.models.operations import Equipment, MaintenanceRequest, OperatingRoom, OperatingRoomBooking
from app.models.user import User

router = APIRouter()
FACILITY_ROLES = ["facilities", "admin", "super_admin"]


class BedStatusUpdate(BaseModel):
    status: str = Field(pattern="^(available|occupied|cleaning|reserved|critical)$")


class MaintenanceCreate(BaseModel):
    description: str = Field(min_length=4, max_length=4000)
    ward_id: str | None = None
    location: str | None = None

    @model_validator(mode="after")
    def require_location(self):
        if not (self.location or self.ward_id):
            raise ValueError("A location or ward identifier is required.")
        return self


@router.get("/beds")
async def list_beds(
    ward: str | None = None,
    current_user: User = Depends(deps.check_role(FACILITY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    query = select(Bed)
    if ward:
        query = query.where(Bed.ward == ward)
    result = await db.execute(query.order_by(Bed.ward, Bed.bed_number))
    return {"items": result.scalars().all()}


@router.get("/wards/{ward_id}/beds")
async def list_ward_beds(
    ward_id: str,
    current_user: User = Depends(deps.check_role(FACILITY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bed).where(Bed.ward == ward_id).order_by(Bed.bed_number))
    return {"items": result.scalars().all()}


@router.put("/beds/{bed_id}/status")
async def update_bed_status(
    bed_id: int,
    update: BedStatusUpdate,
    current_user: User = Depends(deps.check_role(FACILITY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    bed = await db.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    if update.status == "available" and bed.patient_id is not None:
        raise HTTPException(status_code=409, detail="A bed assigned to a patient cannot be marked available.")
    if update.status in {"occupied", "critical"} and bed.patient_id is None:
        raise HTTPException(status_code=409, detail="A patient must be assigned before a bed can be occupied or marked critical.")
    bed.status = update.status
    bed.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(bed)
    return bed


@router.get("/or-schedule")
async def operating_room_schedule(
    current_user: User = Depends(deps.check_role(FACILITY_ROLES + ["doctor", "nurse"])),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(OperatingRoomBooking, OperatingRoom.room_number)
        .join(OperatingRoom, OperatingRoom.id == OperatingRoomBooking.operating_room_id)
        .order_by(OperatingRoomBooking.scheduled_start)
    )
    return {"items": [{
        "id": booking.id,
        "room": room_number,
        "procedure": booking.procedure,
        "scheduled_time": booking.scheduled_start,
        "scheduled_end": booking.scheduled_end,
        "status": booking.status,
        "appointment_id": booking.appointment_id,
    } for booking, room_number in result.all()]}


@router.get("/equipment")
async def equipment_list(
    current_user: User = Depends(deps.check_role(FACILITY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Equipment).order_by(Equipment.location, Equipment.name))
    return {"items": result.scalars().all()}


@router.get("/roster")
async def facilities_roster(
    current_user: User = Depends(deps.check_role(FACILITY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(StaffSchedule, User.role)
        .join(User, User.id == StaffSchedule.staff_id)
        .where(User.role.in_(["facilities", "staff"]))
        .order_by(StaffSchedule.start_time)
    )
    return {"items": [{
        "id": schedule.id,
        "staff_id": schedule.staff_id,
        "role": role,
        "shift": schedule.shift_type,
        "date": schedule.date,
        "shift_start": schedule.start_time,
        "shift_end": schedule.end_time,
        "is_available": schedule.is_available,
    } for schedule, role in result.all()]}


@router.post("/maintenance", status_code=201)
async def create_maintenance_request(
    payload: MaintenanceCreate,
    current_user: User = Depends(deps.check_role(FACILITY_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    request = MaintenanceRequest(
        requested_by_id=current_user.id,
        location=(payload.location or payload.ward_id or "").strip(),
        description=payload.description,
    )
    db.add(request)
    await db.commit()
    await db.refresh(request)
    return request
