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


@router.get("")
@router.get("/")
async def list_departments(db: AsyncSession = Depends(get_db)) -> list[dict[str, object]]:
    result = await db.execute(select(Department).order_by(Department.name.asc()))
    return [_department_payload(item) for item in result.scalars().all()]


@router.get("/{department_id}")
async def get_department(department_id: int, db: AsyncSession = Depends(get_db)) -> dict[str, object]:
    result = await db.execute(select(Department).where(Department.id == department_id))
    department = result.scalar_one_or_none()
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return _department_payload(department)
