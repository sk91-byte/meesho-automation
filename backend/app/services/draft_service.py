import json
import logging
from typing import Optional, Tuple, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy import func

from app.models.conversation import Conversation, ConversationProductMention
from app.models.product import Product, ProductVariant
from app.models.order import OrderDraft, OrderDraftRevision, DraftStatusEnum, Order, OrderItem, OrderStateEnum
from app.models.customer import Customer

logger = logging.getLogger("instagram_reseller")


class MultiProductContextService:
    """Manages multi-product context switching within a single conversation (§3 & §4)."""

    @classmethod
    async def set_active_product_context(
        cls,
        db: AsyncSession,
        conversation_id: str,
        product_id: str
    ) -> ConversationProductMention:
        # Mark all existing mentions for this conversation as inactive
        stmt = select(ConversationProductMention).where(
            ConversationProductMention.conversation_id == conversation_id,
            ConversationProductMention.is_current_active_context == True
        )
        res = await db.execute(stmt)
        active_mentions = res.scalars().all()
        for mention in active_mentions:
            mention.is_current_active_context = False

        # Create or activate new mention
        new_mention = ConversationProductMention(
            conversation_id=conversation_id,
            product_id=product_id,
            is_current_active_context=True
        )
        db.add(new_mention)
        await db.commit()
        await db.refresh(new_mention)
        return new_mention

    @classmethod
    async def get_active_product(cls, db: AsyncSession, conversation_id: str) -> Optional[Product]:
        stmt = (
            select(Product)
            .join(ConversationProductMention, ConversationProductMention.product_id == Product.product_id)
            .where(
                ConversationProductMention.conversation_id == conversation_id,
                ConversationProductMention.is_current_active_context == True,
                Product.active == True
            )
            .order_by(ConversationProductMention.mentioned_at.desc())
        )
        res = await db.execute(stmt)
        return res.scalars().first()


class OrderDraftService:
    """Manages mutable order drafts and revision histories (§5, §6, §7, §8)."""

    @classmethod
    async def get_or_create_draft(cls, db: AsyncSession, conversation_id: str, product_id: Optional[str] = None) -> OrderDraft:
        stmt = select(OrderDraft).options(selectinload(OrderDraft.revisions)).where(
            OrderDraft.conversation_id == conversation_id,
            OrderDraft.status.in_([DraftStatusEnum.DRAFT, DraftStatusEnum.REVIEW_SENT])
        ).order_by(OrderDraft.updated_at.desc())
        res = await db.execute(stmt)
        draft = res.scalars().first()

        if not draft:
            draft = OrderDraft(
                conversation_id=conversation_id,
                product_id=product_id,
                status=DraftStatusEnum.DRAFT
            )
            db.add(draft)
            await db.flush()

            initial_rev = OrderDraftRevision(
                draft_id=draft.draft_id,
                revision_number=1,
                snapshot_data={"status": "DRAFT", "product_id": product_id}
            )
            db.add(initial_rev)
            await db.commit()

            draft = await cls._reload_draft_with_revisions(db, draft.draft_id)
        return draft

    @classmethod
    async def _reload_draft_with_revisions(cls, db: AsyncSession, draft_id: str) -> OrderDraft:
        stmt = select(OrderDraft).options(selectinload(OrderDraft.revisions)).execution_options(populate_existing=True).where(OrderDraft.draft_id == draft_id)
        res = await db.execute(stmt)
        return res.scalars().first()

    @classmethod
    async def update_draft_with_revision(
        cls,
        db: AsyncSession,
        draft: OrderDraft,
        updates: Dict[str, Any]
    ) -> OrderDraft:
        """Applies field changes and appends an audited revision (§6)."""
        changed = False
        for field in ["product_id", "variant_name", "quantity", "customer_name", "phone", "house_building", "road_area_colony", "status"]:
            if field in updates and updates[field] is not None and getattr(draft, field) != updates[field]:
                setattr(draft, field, updates[field])
                changed = True

        if changed:
            count_stmt = select(func.count(OrderDraftRevision.revision_id)).where(OrderDraftRevision.draft_id == draft.draft_id)
            count_res = await db.execute(count_stmt)
            curr_count = count_res.scalar() or 0
            next_rev_num = curr_count + 1

            rev_snapshot = {
                "revision_number": next_rev_num,
                "product_id": draft.product_id,
                "variant_name": draft.variant_name,
                "quantity": draft.quantity,
                "customer_name": draft.customer_name,
                "phone": draft.phone,
                "house_building": draft.house_building,
                "road_area_colony": draft.road_area_colony,
                "status": draft.status.value if isinstance(draft.status, DraftStatusEnum) else str(draft.status)
            }
            revision = OrderDraftRevision(
                draft_id=draft.draft_id,
                revision_number=next_rev_num,
                snapshot_data=rev_snapshot
            )
            db.add(revision)
            await db.commit()
            draft = await cls._reload_draft_with_revisions(db, draft.draft_id)

        return draft

    @classmethod
    def generate_final_order_review_message(cls, draft: OrderDraft, product: Product) -> str:
        """PRD §7 Final Order Review message layout."""
        unit_price = int(product.selling_price)
        total_price = unit_price * draft.quantity
        variant_str = draft.variant_name or "Standard"

        return (
            f"--- ORDER REVIEW ---\n\n"
            f"Product: {product.product_name}\n"
            f"Color/Variant: {variant_str}\n"
            f"Quantity: {draft.quantity}\n"
            f"Price: ₹{unit_price} each\n"
            f"Total: ₹{total_price}\n\n"
            f"Customer: {draft.customer_name or 'N/A'}\n"
            f"Mobile: {draft.phone or 'N/A'}\n"
            f"House/Building: {draft.house_building or 'N/A'}\n"
            f"Road/Area/Colony: {draft.road_area_colony or 'N/A'}\n\n"
            f"Please check all details carefully.\n"
            f"Reply 'CONFIRM' to finalize your order, or 'CHANGE' to edit details!"
        )

    @classmethod
    async def double_check_and_confirm_order(
        cls,
        db: AsyncSession,
        draft: OrderDraft,
        customer: Customer
    ) -> Tuple[bool, Optional[Order], str]:
        """
        PRD §8 Verification Procedure:
        Reload product & variant -> Check stock & price -> Atomic SQL Transaction.
        """
        if not draft.product_id:
            return False, None, "No product selected in order draft."

        # 1. Reload product directly from DB
        prod_res = await db.execute(select(Product).where(Product.product_id == draft.product_id))
        product = prod_res.scalars().first()
        if not product or not product.active:
            return False, None, "Product is no longer active or available."

        # 2. Reload variant availability if specified
        if draft.variant_name:
            var_stmt = select(ProductVariant).where(
                ProductVariant.product_id == product.product_id,
                ProductVariant.value.ilike(draft.variant_name)
            )
            var_res = await db.execute(var_stmt)
            variant = var_res.scalars().first()
            if variant and not variant.available:
                return False, None, f"Variant '{draft.variant_name}' is out of stock."

        # 3. Verify required customer details
        if not (draft.customer_name and draft.phone and draft.house_building and draft.road_area_colony):
            return False, None, "Missing mandatory delivery details."

        # 4. Atomic DB Transaction for confirmed order creation
        total_selling = product.selling_price * draft.quantity
        total_cost = product.actual_price * draft.quantity
        margin = total_selling - total_cost

        confirmed_order = Order(
            customer_id=customer.customer_id,
            conversation_id=draft.conversation_id,
            draft_id=draft.draft_id,
            order_state=OrderStateEnum.CONFIRMED,
            customer_name=draft.customer_name,
            phone=draft.phone,
            house_building=draft.house_building,
            road_area_colony=draft.road_area_colony,
            total_selling_price=total_selling,
            total_actual_cost=total_cost,
            expected_margin=margin,
            payment_method="COD"
        )
        db.add(confirmed_order)
        await db.flush()

        order_item = OrderItem(
            order_id=confirmed_order.order_id,
            product_id=product.product_id,
            product_name=product.product_name,
            actual_price=product.actual_price,
            selling_price=product.selling_price,
            variant=draft.variant_name or "Standard",
            quantity=draft.quantity
        )
        db.add(order_item)

        draft.status = DraftStatusEnum.CONFIRMED
        await db.commit()
        await db.refresh(confirmed_order)

        return True, confirmed_order, "Order confirmed successfully!"
