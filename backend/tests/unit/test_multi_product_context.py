import pytest
import pytest_asyncio
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload

from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.product import Product, ProductVariant
from app.models.order import OrderDraft, OrderDraftRevision, DraftStatusEnum, OrderStateEnum, Order
from app.services.draft_service import MultiProductContextService, OrderDraftService


@pytest_asyncio.fixture(autouse=True)
async def prepare_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_critical_multi_product_context_switch():
    """PRD §68: Verify switching Bag -> Watch -> Bag isolates order context."""
    async with AsyncSessionLocal() as session:
        # Create Bag and Watch
        bag = Product(sku="BAG-001", product_name="Women's Sling Bag", actual_price=299.0, selling_price=449.0)
        watch = Product(sku="WATCH-001", product_name="Smartwatch", actual_price=799.0, selling_price=1299.0)
        session.add_all([bag, watch])
        await session.commit()

        customer = Customer(instagram_user_id="ig_multi_user")
        session.add(customer)
        await session.commit()

        conv = Conversation(customer_id=customer.customer_id)
        session.add(conv)
        await session.commit()

        # Step 1: Customer discusses Bag
        await MultiProductContextService.set_active_product_context(session, conv.conversation_id, bag.product_id)
        active_1 = await MultiProductContextService.get_active_product(session, conv.conversation_id)
        assert active_1.product_name == "Women's Sling Bag"

        # Step 2: Customer asks about Smartwatch
        await MultiProductContextService.set_active_product_context(session, conv.conversation_id, watch.product_id)
        active_2 = await MultiProductContextService.get_active_product(session, conv.conversation_id)
        assert active_2.product_name == "Smartwatch"

        # Step 3: Customer switches back to Bag
        await MultiProductContextService.set_active_product_context(session, conv.conversation_id, bag.product_id)
        active_3 = await MultiProductContextService.get_active_product(session, conv.conversation_id)
        assert active_3.product_name == "Women's Sling Bag"

        # Step 4: Draft creation relies ONLY on active Bag context
        draft = await OrderDraftService.get_or_create_draft(session, conv.conversation_id, active_3.product_id)
        assert draft.product_id == bag.product_id
        assert draft.product_id != watch.product_id


@pytest.mark.asyncio
async def test_order_draft_revision_history():
    """PRD §6: Verify draft revision versioning audit log."""
    async with AsyncSessionLocal() as session:
        customer = Customer(instagram_user_id="ig_rev_user")
        session.add(customer)
        await session.commit()

        conv = Conversation(customer_id=customer.customer_id)
        session.add(conv)
        await session.commit()

        bag = Product(sku="BAG-REV", product_name="Sling Bag", actual_price=200.0, selling_price=350.0)
        session.add(bag)
        await session.commit()

        draft = await OrderDraftService.get_or_create_draft(session, conv.conversation_id, bag.product_id)

        # Revision 1: Black x 2
        await OrderDraftService.update_draft_with_revision(session, draft, {"variant_name": "Black", "quantity": 2})
        # Revision 2: Brown x 2
        await OrderDraftService.update_draft_with_revision(session, draft, {"variant_name": "Brown"})
        # Revision 3: Brown x 3
        await OrderDraftService.update_draft_with_revision(session, draft, {"quantity": 3})

        stmt = select(OrderDraft).options(selectinload(OrderDraft.revisions)).where(OrderDraft.draft_id == draft.draft_id)
        res = await session.execute(stmt)
        updated_draft = res.scalars().first()

        assert len(updated_draft.revisions) == 4  # Initial + 3 updates
        assert updated_draft.variant_name == "Brown"
        assert updated_draft.quantity == 3


@pytest.mark.asyncio
async def test_pre_confirmation_double_check_verification():
    """PRD §8: Pre-confirmation reload and atomic verification."""
    async with AsyncSessionLocal() as session:
        customer = Customer(
            instagram_user_id="ig_confirm_user",
            name="Rahul",
            phone="9876543210",
            house_building="B-42",
            road_area_colony="Sector 7"
        )
        session.add(customer)
        await session.commit()

        conv = Conversation(customer_id=customer.customer_id)
        session.add(conv)
        await session.commit()

        bag = Product(sku="BAG-CONFIRM", product_name="Women's Sling Bag", actual_price=299.0, selling_price=449.0)
        session.add(bag)
        await session.commit()

        draft = await OrderDraftService.get_or_create_draft(session, conv.conversation_id, bag.product_id)
        await OrderDraftService.update_draft_with_revision(session, draft, {
            "variant_name": "Brown",
            "quantity": 3,
            "customer_name": customer.name,
            "phone": customer.phone,
            "house_building": customer.house_building,
            "road_area_colony": customer.road_area_colony
        })

        success, confirmed_order, msg = await OrderDraftService.double_check_and_confirm_order(session, draft, customer)
        assert success is True
        assert confirmed_order.total_selling_price == 1347.0
        assert confirmed_order.total_actual_cost == 897.0
        assert confirmed_order.expected_margin == 450.0
        assert draft.status == DraftStatusEnum.CONFIRMED
