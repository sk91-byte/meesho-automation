from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import func

from app.api.deps import get_db, get_current_user
from app.models.user import User
from app.models.order import Order, OrderStateEnum
from app.models.conversation import Conversation
from app.models.customer import CustomerRequest

router = APIRouter(prefix="/analytics", tags=["Nightly Business Analytics"])


@router.get("/nightly-summary")
async def get_nightly_business_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> Dict[str, Any]:
    """Generates a business summary report strictly calculated from database facts."""
    # Orders & Financials
    orders_res = await db.execute(select(Order).where(Order.order_state == OrderStateEnum.CONFIRMED))
    confirmed_orders = orders_res.scalars().all()
    
    total_orders = len(confirmed_orders)
    total_revenue = sum(o.total_selling_price for o in confirmed_orders)
    total_expected_margin = sum(o.expected_margin for o in confirmed_orders)

    # Conversation statistics
    conv_res = await db.execute(select(Conversation))
    all_conversations = conv_res.scalars().all()
    total_conversations = len(all_conversations)
    human_review_count = sum(1 for c in all_conversations if c.requires_human_review)

    # Top requested variants
    req_res = await db.execute(
        select(CustomerRequest.requested_value, func.count(CustomerRequest.request_id).label("count"))
        .group_by(CustomerRequest.requested_value)
        .order_by(func.count(CustomerRequest.request_id).desc())
        .limit(5)
    )
    top_requests = [{"value": r[0], "count": r[1]} for r in req_res.all()]

    return {
        "summary": {
            "total_orders": total_orders,
            "total_revenue": total_revenue,
            "expected_gross_margin": total_expected_margin,
            "total_conversations": total_conversations,
            "human_review_queue_count": human_review_count,
            "top_requested_variants": top_requests
        },
        "nightly_report_formatted": (
            f"--- TONIGHT'S BUSINESS SUMMARY ---\n"
            f"• Orders Completed: {total_orders}\n"
            f"• Expected Revenue: ₹{int(total_revenue)}\n"
            f"• Expected Gross Margin: ₹{int(total_expected_margin)}\n"
            f"• Customer Conversations: {total_conversations}\n"
            f"• Needs Human Attention: {human_review_count}\n"
            f"• Top Requested Variant: {top_requests[0]['value'] if top_requests else 'None'}"
        )
    }
