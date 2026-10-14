from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.bed import Bed
from app.models.operations import Equipment, OperatingRoom
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


class ResourceStatus(BaseModel):
    status: str = Field(min_length=2, max_length=30)


class RoomBlock(BaseModel):
    room_id: int = Field(gt=0)
    reason: str = Field(min_length=3, max_length=1000)


class EquipmentCreate(BaseModel):
    asset_tag: str = Field(min_length=2, max_length=80)
    name: str = Field(min_length=2, max_length=160)
    category: str = Field(min_length=2, max_length=100)
    location: str = Field(min_length=1, max_length=160)
    status: str = "available"


class EquipmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=160)
    category: str | None = None
    location: str | None = None
    status: str | None = None
    last_maintenance: datetime | None = None


@router.get("/beds")
async def list_beds(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Bed).order_by(Bed.ward, Bed.bed_number))
    return {"items": result.scalars().all()}


@router.put("/beds/{bed_id}")
async def update_bed(bed_id: int, payload: ResourceStatus, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"available", "occupied", "cleaning", "reserved", "critical"}:
        raise HTTPException(status_code=422, detail="Unsupported bed status.")
    bed = await db.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    if payload.status == "available" and bed.patient_id is not None:
        raise HTTPException(status_code=409, detail="A bed assigned to a patient cannot be made available.")
    if payload.status in {"occupied", "critical"} and bed.patient_id is None:
        raise HTTPException(status_code=409, detail="A patient must be assigned to occupy this bed.")
    bed.status = payload.status
    bed.updated_at = datetime.utcnow()
    await db.commit()
    return {"id": bed.id, "status": bed.status}


@router.get("/ors")
async def list_operating_rooms(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(OperatingRoom).order_by(OperatingRoom.floor, OperatingRoom.room_number))
    return {"items": result.scalars().all()}


@router.post("/ors/block")
async def block_operating_room(payload: RoomBlock, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    room = await db.get(OperatingRoom, payload.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Operating room not found.")
    room.status = "blocked"
    room.status_reason = payload.reason.strip()
    await db.commit()
    return {"id": room.id, "status": room.status, "status_reason": room.status_reason}


@router.put("/ors/{room_id}")
async def update_operating_room(room_id: int, payload: ResourceStatus, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"available", "blocked", "maintenance", "in_use"}:
        raise HTTPException(status_code=422, detail="Unsupported operating room status.")
    room = await db.get(OperatingRoom, room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="Operating room not found.")
    room.status = payload.status
    if payload.status == "available":
        room.status_reason = None
    await db.commit()
    return {"id": room.id, "status": room.status, "status_reason": room.status_reason}


@router.get("/equipment")
async def list_equipment(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Equipment).order_by(Equipment.location, Equipment.name))
    return {"items": result.scalars().all()}


@router.post("/equipment", status_code=status.HTTP_201_CREATED)
async def create_equipment(payload: EquipmentCreate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(Equipment.id).where(Equipment.asset_tag == payload.asset_tag.strip()))
    if exists is not None:
        raise HTTPException(status_code=409, detail="Asset tag is already in use.")
    equipment = Equipment(**{**payload.model_dump(), "asset_tag": payload.asset_tag.strip(), "name": payload.name.strip(), "category": payload.category.strip(), "location": payload.location.strip()})
    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)
    return equipment


@router.put("/equipment/{equipment_id}")
async def update_equipment(equipment_id: int, payload: EquipmentUpdate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    equipment = await db.get(Equipment, equipment_id)
    if equipment is None:
        raise HTTPException(status_code=404, detail="Equipment record not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(equipment, key, value)
    await db.commit()
    await db.refresh(equipment)
    return equipment
