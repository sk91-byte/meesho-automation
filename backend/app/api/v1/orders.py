from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.order import Order, OrderStateEnum

router = APIRouter(prefix="/orders", tags=["Order Management Center"])


@router.get("/")
async def list_orders(
    order_state: Optional[OrderStateEnum] = Query(None, description="Filter by order state"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Order).options(selectinload(Order.items))
    if order_state:
        stmt = stmt.where(Order.order_state == order_state)
    stmt = stmt.order_by(Order.created_at.desc())
    result = await db.execute(stmt)
    return result.scalars().all()


@router.get("/{order_id}")
async def get_order_details(
    order_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    stmt = select(Order).options(selectinload(Order.items)).where(Order.order_id == order_id)
    result = await db.execute(stmt)
    order = result.scalars().first()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return order
