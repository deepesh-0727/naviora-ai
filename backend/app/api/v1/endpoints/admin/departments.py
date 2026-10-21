from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.appointment import Appointment
from app.models.doctor import Department, Doctor
from app.models.operations import DepartmentWaypoint
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


class DepartmentCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    description: str | None = None
    floor: int
    building: str = Field(min_length=1, max_length=50)
    wing: str = Field(min_length=1, max_length=50)
    phone: str = Field(min_length=7, max_length=20)
    email: EmailStr


class DepartmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=100)
    description: str | None = None
    floor: int | None = None
    building: str | None = Field(default=None, max_length=50)
    wing: str | None = Field(default=None, max_length=50)
    phone: str | None = Field(default=None, max_length=20)
    email: EmailStr | None = None


class WaypointCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    floor: int
    building: str = Field(min_length=1, max_length=80)
    x_coordinate: float
    y_coordinate: float
    connected_to_id: int | None = None


@router.get("")
async def list_departments(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Department).order_by(Department.name))
    return {"items": [
        {
            "id": department.id,
            "name": department.name,
            "description": department.description,
            "floor": department.floor,
            "building": department.building,
            "wing": department.wing,
            "phone": department.phone,
            "email": department.email,
        }
        for department in result.scalars().all()
    ]}


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_department(payload: DepartmentCreate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    exists = await db.scalar(select(Department.id).where(Department.name == payload.name.strip()))
    if exists is not None:
        raise HTTPException(status_code=409, detail="Department name already exists.")
    department = Department(**payload.model_dump(exclude={"name", "email"}), name=payload.name.strip(), email=str(payload.email))
    db.add(department)
    await db.commit()
    await db.refresh(department)
    return department


@router.get("/{department_id}")
async def get_department(department_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    department = await db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    return department


@router.put("/{department_id}")
async def update_department(department_id: int, payload: DepartmentUpdate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    department = await db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    values = payload.model_dump(exclude_unset=True)
    if values.get("email") is not None:
        values["email"] = str(values["email"])
    if values.get("name") is not None:
        exists = await db.scalar(select(Department.id).where(Department.name == values["name"], Department.id != department_id))
        if exists is not None:
            raise HTTPException(status_code=409, detail="Department name already exists.")
        values["name"] = values["name"].strip()
    for key, value in values.items():
        setattr(department, key, value)
    await db.commit()
    await db.refresh(department)
    return department


@router.delete("/{department_id}")
async def delete_department(department_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    department = await db.get(Department, department_id)
    if department is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    linked_doctor = await db.scalar(select(Doctor.id).where(Doctor.department_id == department_id).limit(1))
    linked_appointment = await db.scalar(select(Appointment.id).where(Appointment.department_id == department_id).limit(1))
    if linked_doctor is not None or linked_appointment is not None:
        raise HTTPException(status_code=409, detail="Department has linked doctors or appointments and cannot be deleted.")
    await db.delete(department)
    await db.commit()
    return {"id": department_id, "deleted": True}


@router.get("/{department_id}/doctors")
async def department_doctors(department_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if await db.get(Department, department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    result = await db.execute(select(Doctor).where(Doctor.department_id == department_id).order_by(Doctor.last_name, Doctor.first_name))
    return {"items": result.scalars().all()}


@router.get("/{department_id}/waypoints")
async def department_waypoints(department_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if await db.get(Department, department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    result = await db.execute(select(DepartmentWaypoint).where(DepartmentWaypoint.department_id == department_id).order_by(DepartmentWaypoint.floor, DepartmentWaypoint.name))
    return {"items": result.scalars().all()}


@router.post("/{department_id}/waypoints", status_code=status.HTTP_201_CREATED)
async def create_waypoint(department_id: int, payload: WaypointCreate, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    if await db.get(Department, department_id) is None:
        raise HTTPException(status_code=404, detail="Department not found.")
    if payload.connected_to_id is not None:
        connected = await db.get(DepartmentWaypoint, payload.connected_to_id)
        if connected is None or connected.department_id != department_id:
            raise HTTPException(status_code=422, detail="Connected waypoint must belong to this department.")
    waypoint = DepartmentWaypoint(department_id=department_id, **payload.model_dump())
    db.add(waypoint)
    await db.commit()
    await db.refresh(waypoint)
    return waypoint
