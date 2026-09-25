import pytest
import pytest_asyncio
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.customer import Customer
from app.models.conversation import Conversation
from app.models.product import Product
from app.models.order import Order, OrderStateEnum
from app.services.order_service import OrderStateMachine


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_order_state_machine_missing_fields():
    async with AsyncSessionLocal() as session:
        customer = Customer(instagram_user_id="ig_user_001")
        session.add(customer)
        await session.commit()
        await session.refresh(customer)

        conversation = Conversation(customer_id=customer.customer_id)
        session.add(conversation)
        await session.commit()
        await session.refresh(conversation)

        product = Product(
            sku="BAG-01",
            product_name="Test Sling Bag",
            actual_price=200.0,
            selling_price=350.0
        )
        session.add(product)
        await session.commit()
        await session.refresh(product)

        # Step 1: Provide name only
        extracted_1 = {"customer_name": "Rahul"}
        state_1, missing_1, prompt_1 = await OrderStateMachine.process_order_step(
            session, customer, conversation, product, extracted_1
        )

        assert state_1 == OrderStateEnum.COLLECTING_DETAILS
        assert missing_1 == ["phone", "house_building", "road_area_colony"]
        assert "mobile number" in prompt_1.lower()

        # Step 2: Provide all remaining details
        extracted_2 = {
            "phone": "9876543210",
            "house_building": "Flat 4B",
            "road_area_colony": "MG Road"
        }
        state_2, missing_2, prompt_2 = await OrderStateMachine.process_order_step(
            session, customer, conversation, product, extracted_2
        )

        assert state_2 == OrderStateEnum.READY_FOR_CONFIRMATION
        assert missing_2 == []
        assert "CONFIRM" in prompt_2


@pytest.mark.asyncio
async def test_create_confirmed_order_snapshot():
    async with AsyncSessionLocal() as session:
        customer = Customer(
            instagram_user_id="ig_user_002",
            name="Priya",
            phone="9998887770",
            house_building="H.No 12",
            road_area_colony="Sector 15"
        )
        session.add(customer)
        await session.commit()

        conversation = Conversation(customer_id=customer.customer_id)
        session.add(conversation)
        await session.commit()

        product = Product(
            sku="DRESS-01",
            product_name="Summer Dress",
            actual_price=400.0,  # Cost
            selling_price=699.0  # Price
        )
        session.add(product)
        await session.commit()

        created_order = await OrderStateMachine.create_confirmed_order_transaction(
            session, customer, conversation, product, variant_name="Red - M", quantity=2
        )

        # Query order with selectinload for async relationship access
        stmt = select(Order).options(selectinload(Order.items)).where(Order.order_id == created_order.order_id)
        res = await session.execute(stmt)
        order = res.scalars().first()

        assert order.total_selling_price == 1398.0
        assert order.total_actual_cost == 800.0
        assert order.expected_margin == 598.0
        assert order.order_state == OrderStateEnum.CONFIRMED
        assert len(order.items) == 1
        assert order.items[0].product_name == "Summer Dress"
        assert order.items[0].actual_price == 400.0
        assert order.items[0].selling_price == 699.0
