from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.db.session import get_db
from app.services.location_service import location_service
from app.schemas.location import LocationUpdate, Location as LocationSchema

router = APIRouter()

@router.post("/update", response_model=LocationSchema)
async def update_location(data: LocationUpdate, db: AsyncSession = Depends(get_db)):
    """
    Update the user's current location.
    """
    location = await location_service.update_location(
        db,
        user_id=data.user_id,
        lat=data.latitude,
        lon=data.longitude,
        floor=data.floor,
        building=data.building
    )
    return location

@router.get("/staff/nearby")
async def get_nearby_staff(building: str, floor: int, db: AsyncSession = Depends(get_db)):
    """
    Find staff members on a specific floor/building.
    """
    staff = await location_service.get_nearby_staff(db, building, floor)
    return staff
