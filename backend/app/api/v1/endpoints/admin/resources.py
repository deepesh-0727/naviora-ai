from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.bed import Bed
from app.models.operations import Admission, Equipment, OperatingRoom
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


class ResourceStatus(BaseModel):
    status: str = Field(min_length=2, max_length=30)


class BedCreate(BaseModel):
    bed_number: str = Field(min_length=1, max_length=40)
    ward: str = Field(min_length=1, max_length=100)
    floor: int
    status: str = "available"


class BedUpdate(BaseModel):
    bed_number: str | None = Field(default=None, min_length=1, max_length=40)
    ward: str | None = Field(default=None, min_length=1, max_length=100)
    floor: int | None = None
    status: str | None = Field(default=None, min_length=2, max_length=20)


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


@router.post("/beds", status_code=status.HTTP_201_CREATED)
async def create_bed(payload: BedCreate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if payload.status not in {"available", "occupied", "cleaning", "reserved", "critical"}:
        raise HTTPException(status_code=422, detail="Unsupported bed status.")
    if await db.scalar(select(Bed.id).where(Bed.ward == payload.ward.strip(), Bed.bed_number == payload.bed_number.strip())) is not None:
        raise HTTPException(status_code=409, detail="That bed number already exists in this ward.")
    if payload.status in {"occupied", "critical"}:
        raise HTTPException(status_code=422, detail="Beds must be assigned to a patient before they can be marked occupied or critical.")
    bed = Bed(ward=payload.ward.strip(), bed_number=payload.bed_number.strip(), floor=payload.floor, status=payload.status)
    db.add(bed)
    await db.commit()
    await db.refresh(bed)
    return bed


@router.put("/beds/{bed_id}")
async def update_bed(bed_id: int, payload: BedUpdate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    updates = payload.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=422, detail="Provide at least one bed field to update.")
    if updates.get("status") is not None and updates["status"] not in {"available", "occupied", "cleaning", "reserved", "critical"}:
        raise HTTPException(status_code=422, detail="Unsupported bed status.")
    bed = await db.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    if updates.get("status") == "available" and bed.patient_id is not None:
        raise HTTPException(status_code=409, detail="A bed assigned to a patient cannot be made available.")
    if updates.get("status") in {"occupied", "critical"} and bed.patient_id is None:
        raise HTTPException(status_code=409, detail="A patient must be assigned to occupy this bed.")
    ward = str(updates.get("ward", bed.ward)).strip()
    bed_number = str(updates.get("bed_number", bed.bed_number)).strip()
    duplicate = await db.scalar(select(Bed.id).where(Bed.ward == ward, Bed.bed_number == bed_number, Bed.id != bed_id))
    if duplicate is not None:
        raise HTTPException(status_code=409, detail="That bed number already exists in this ward.")
    for key, value in updates.items():
        setattr(bed, key, value.strip() if key in {"ward", "bed_number"} and value is not None else value)
    bed.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(bed)
    return bed


@router.delete("/beds/{bed_id}")
async def delete_bed(bed_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    bed = await db.get(Bed, bed_id)
    if bed is None:
        raise HTTPException(status_code=404, detail="Bed not found.")
    if bed.patient_id is not None or bed.status in {"occupied", "critical"}:
        raise HTTPException(status_code=409, detail="A bed assigned to a patient cannot be deleted.")
    linked_admission = await db.scalar(select(Admission.id).where(Admission.bed_id == bed_id).limit(1))
    if linked_admission is not None:
        raise HTTPException(status_code=409, detail="A bed linked to an admission cannot be deleted.")
    await db.delete(bed)
    await db.commit()
    return {"id": bed_id, "deleted": True}


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
