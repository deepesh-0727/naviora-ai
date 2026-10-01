from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
import datetime

from app.db.session import get_db
from app.models.user import User
from app.models.doctor import Doctor, Department
from app.models.hospital import AuditLog
from app.api import deps
from app.core import security
from app.services.analytics.analytics_service import analytics_service

router = APIRouter()

# --- Pydantic Schemas for Admin Operations ---

class StaffCreate(BaseModel):
    first_name: str
    last_name: str
    email: str
    phone: str
    role: str # doctor, nurse, coordinator, admin
    specialization: Optional[str] = "General Medicine"
    department_id: Optional[int] = 1

class StaffUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None

class DepartmentCreate(BaseModel):
    name: str
    description: Optional[str] = None
    floor: int
    building: str
    wing: str
    phone: str
    email: str

# --- 1. Staff Management (Full CRUD) ---

@router.get("/staff")
async def list_staff(
    role: Optional[str] = Query(None),
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """List all clinical and administrative staff members."""
    query = select(User).filter(User.role.in_(["doctor", "staff", "nurse", "admin"]))
    if role:
        query = query.filter(User.role == role)
    
    result = await db.execute(query)
    users = result.scalars().all()

    return [
        {
            "id": u.id,
            "email": u.email,
            "phone": u.phone,
            "role": u.role,
            "is_active": u.is_active,
            "created_at": u.created_at
        }
        for u in users
    ]

@router.post("/staff", status_code=status.HTTP_201_CREATED)
async def add_staff(
    staff: StaffCreate,
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Onboard a new staff member (Doctor, Nurse, or Admin)."""
    new_user = User(
        email=staff.email,
        phone=staff.phone,
        password_hash=security.get_password_hash("NavioraTemp123!"),
        role=staff.role,
        is_active=True,
        is_verified=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)

    if staff.role == "doctor":
        new_doc = Doctor(
            user_id=new_user.id,
            first_name=staff.first_name,
            last_name=staff.last_name,
            specialization=staff.specialization,
            department_id=staff.department_id,
            license_number=f"LIC-{new_user.id:05d}",
            years_of_experience=0,
            is_available=True
        )
        db.add(new_doc)
        await db.commit()

    return {"message": "Staff member onboarded successfully", "id": new_user.id}

@router.put("/staff/{id}")
async def update_staff(
    id: int,
    staff_update: StaffUpdate,
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Update staff credentials and role status."""
    result = await db.execute(select(User).filter(User.id == id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    if staff_update.role:
        user.role = staff_update.role
    if staff_update.is_active is not None:
        user.is_active = staff_update.is_active

    await db.commit()
    return {"message": f"Staff member {id} updated successfully"}

@router.delete("/staff/{id}")
async def deactivate_staff(
    id: int,
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate or remove a staff member (Soft Delete)."""
    result = await db.execute(select(User).filter(User.id == id))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Staff member not found.")

    user.is_active = False
    await db.commit()
    return {"message": f"Staff member {id} deactivated successfully"}

# --- 2. Department Management ---

@router.get("/departments")
async def list_departments(
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve hospital wings and department details."""
    result = await db.execute(select(Department))
    return result.scalars().all()

@router.post("/departments", status_code=status.HTTP_201_CREATED)
async def add_department(
    dept: DepartmentCreate,
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Create a new hospital department node."""
    new_dept = Department(
        name=dept.name,
        description=dept.description,
        floor=dept.floor,
        building=dept.building,
        wing=dept.wing,
        phone=dept.phone,
        email=dept.email
    )
    db.add(new_dept)
    await db.commit()
    await db.refresh(new_dept)
    return new_dept

# --- 3. Clinical Intelligence & Audit ---

@router.get("/analytics")
async def get_hospital_analytics(
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Real-time clinical throughput and performance metrics."""
    return await analytics_service.get_hospital_kpis(db)

@router.get("/reports")
async def generate_facility_reports(
    current_admin: User = Depends(deps.check_role(["admin"]))
):
    """Generate hospital operational and financial reports."""
    return {
        "generated_at": datetime.datetime.utcnow().isoformat(),
        "available_reports": [
            {"title": "Patient Flow Summary", "format": "PDF", "id": "REP-001"},
            {"title": "Pharmacy Turnover", "format": "XLSX", "id": "REP-002"},
            {"title": "Emergency Dispatch Performance", "format": "PDF", "id": "REP-003"}
        ]
    }

@router.get("/audit-logs")
async def get_compliance_audit_logs(
    limit: int = Query(100, le=1000),
    current_admin: User = Depends(deps.check_role(["admin"])),
    db: AsyncSession = Depends(get_db)
):
    """Retrieve HIPAA & GDPR compliance audit trails."""
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit))
    return result.scalars().all()
