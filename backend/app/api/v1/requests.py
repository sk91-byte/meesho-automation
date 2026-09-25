from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.deps import get_db, get_current_user, require_roles
from app.models.user import User, RoleEnum
from app.models.customer import CustomerRequest, RequestTypeEnum, RequestStatusEnum

router = APIRouter(prefix="/requests", tags=["Customer Requests Analytics"])


@router.get("/")
async def list_customer_requests(
    request_type: Optional[RequestTypeEnum] = Query(None, description="Filter request type"),
    status: Optional[RequestStatusEnum] = Query(None, description="Filter request status"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(CustomerRequest)
    if request_type:
        stmt = stmt.where(CustomerRequest.request_type == request_type)
    if status:
        stmt = stmt.where(CustomerRequest.status == status)
    stmt = stmt.order_by(CustomerRequest.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/summary")
async def get_request_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Aggregate customer requests by requested value (e.g. Blue: 7 requests, XL: 4 requests)."""
    stmt = (
        select(CustomerRequest.requested_value, CustomerRequest.request_type, func.count(CustomerRequest.request_id).label("count"))
        .group_by(CustomerRequest.requested_value, CustomerRequest.request_type)
        .order_by(func.count(CustomerRequest.request_id).desc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    return [{"value": r[0], "type": r[1], "count": r[2]} for r in rows]
