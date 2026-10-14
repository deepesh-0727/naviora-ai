import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.hospital import AuditLog
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


@router.get("")
async def list_audit_logs(limit: int = 100, offset: int = 0, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    safe_limit = min(max(limit, 1), 1000)
    safe_offset = max(offset, 0)
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).offset(safe_offset).limit(safe_limit))
    return {"items": result.scalars().all(), "limit": safe_limit, "offset": safe_offset}


@router.get("/{audit_id}")
async def audit_log_detail(audit_id: int, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    entry = await db.get(AuditLog, audit_id)
    if entry is None:
        raise HTTPException(status_code=404, detail="Audit record not found.")
    return entry


@router.get("/export/csv")
async def export_audit_logs(limit: int = 10000, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    safe_limit = min(max(limit, 1), 50000)
    result = await db.execute(select(AuditLog).order_by(AuditLog.created_at.desc()).limit(safe_limit))
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["id", "user_id", "action", "resource", "method", "resource_id", "status", "ip_address", "duration_ms", "created_at"])
    for entry in result.scalars().all():
        writer.writerow([entry.id, entry.user_id, entry.action, entry.resource, entry.method, entry.resource_id, entry.status, entry.ip_address, entry.duration_ms, entry.created_at])
    buffer.seek(0)
    return StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=naviora-audit.csv"})
