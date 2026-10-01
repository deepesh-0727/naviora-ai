from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List

from app.db.session import get_db
from app.models.doctor import Department
from app.services.navigation.route_planner import route_planner

router = APIRouter()

@router.get("/departments")
async def list_departments(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department))
    return result.scalars().all()

@router.get("/departments/{id}")
async def get_department(id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).filter(Department.id == id))
    return result.scalars().first()

@router.post("/route")
async def get_navigation_route(start_node: str, end_node: str, accessible: bool = False):
    path_data = route_planner.find_path(start_node, end_node, needs_accessible=accessible)
    if not path_data or "error" in path_data:
        return {"error": "Path not found", "path": []}
    return path_data

@router.post("/location")
async def update_patient_location(user_id: int, latitude: float, longitude: float, floor: int = 0):
    return {
        "status": "success",
        "user_id": user_id,
        "location": {"latitude": latitude, "longitude": longitude, "floor": floor},
        "message": "Location updated successfully"
    }

@router.get("/poi")
async def get_points_of_interest():
    return {
        "pois": [
            {"name": "Restroom A", "location": "Ground Floor"},
            {"name": "Cafeteria", "location": "1st Floor"},
            {"name": "Prayer Room", "location": "Basement"}
        ]
    }

@router.get("/floor-map")
async def get_floor_map(floor: int):
    return {"floor": floor, "map_url": f"https://cdn.naviora.ai/maps/floor_{floor}.svg"}
