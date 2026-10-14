from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.db.session import get_db
from app.models.billing import Billing
from app.models.operations import BillingRefund
from app.models.user import User

router = APIRouter()
ADMIN_ROLES = ["admin", "super_admin"]


class RefundRequest(BaseModel):
    billing_id: int = Field(gt=0)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    reason: str = Field(min_length=3, max_length=4000)


@router.get("/bills")
async def list_bills(limit: int = 100, offset: int = 0, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Billing).order_by(Billing.created_at.desc()).offset(max(offset, 0)).limit(min(max(limit, 1), 1000)))
    return {"items": result.scalars().all()}


@router.get("/invoices")
async def list_invoices(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Billing).order_by(Billing.created_at.desc()))
    return {"items": result.scalars().all()}


@router.get("/payments")
async def list_payments(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Billing).where(Billing.status == "paid").order_by(Billing.updated_at.desc()))
    return {"items": result.scalars().all()}


@router.get("/revenue")
async def revenue_summary(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(func.date(Billing.updated_at), func.sum(Billing.amount), func.count(Billing.id)).where(Billing.status == "paid").group_by(func.date(Billing.updated_at)).order_by(func.date(Billing.updated_at)))
    return {"items": [{"date": str(day), "revenue": str(amount or Decimal("0.00")), "payment_count": count} for day, amount, count in result.all()]}


@router.get("/refunds")
async def list_refunds(current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(BillingRefund).order_by(BillingRefund.created_at.desc()))
    return {"items": result.scalars().all()}


@router.post("/refunds", status_code=status.HTTP_201_CREATED)
async def request_refund(payload: RefundRequest, current_user: User = Depends(deps.check_role(ADMIN_ROLES)), db: AsyncSession = Depends(get_db)):
    bill = await db.get(Billing, payload.billing_id)
    if bill is None:
        raise HTTPException(status_code=404, detail="Bill not found.")
    if bill.status != "paid":
        raise HTTPException(status_code=409, detail="Only paid bills can be refunded.")
    if payload.amount > bill.amount:
        raise HTTPException(status_code=422, detail="Refund amount cannot exceed the original payment.")
    refund = BillingRefund(billing_id=bill.id, requested_by_id=current_user.id, amount=payload.amount, reason=payload.reason.strip())
    db.add(refund)
    await db.commit()
    await db.refresh(refund)
    return refund
