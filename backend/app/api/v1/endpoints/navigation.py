from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.doctor import Department

router = APIRouter()


def _department_payload(department: Department) -> dict[str, object]:
    return {
        "id": department.id,
        "name": department.name,
        "description": department.description,
        "floor": department.floor,
        "building": department.building,
        "wing": department.wing,
        "phone": department.phone,
        "email": department.email,
    }


@router.get("/departments")
async def list_departments(db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    result = await db.execute(select(Department).order_by(Department.name.asc()))
    return [_department_payload(item) for item in result.scalars().all()]


@router.get("/departments/{id}")
async def get_department(id: int, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    result = await db.execute(select(Department).where(Department.id == id))
    department = result.scalar_one_or_none()
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return _department_payload(department)


@router.get("/route")
async def get_navigation_route():
    raise HTTPException(status_code=501, detail="Indoor routes are not configured for this hospital.")


@router.post("/route")
async def create_navigation_route():
    raise HTTPException(status_code=501, detail="Indoor routes are not configured for this hospital.")


@router.get("/poi")
async def get_points_of_interest():
    raise HTTPException(status_code=501, detail="Points of interest are not configured for this hospital.")


@router.get("/floor-map")
async def get_floor_map(floor: int):
    raise HTTPException(status_code=501, detail="Floor maps are not configured for this hospital.")
