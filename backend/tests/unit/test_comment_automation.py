import pytest
import pytest_asyncio
from sqlalchemy.future import select

from app.core.database import AsyncSessionLocal, async_engine, Base
from app.models.product import Product, ProductVariant
from app.models.customer import Customer
from app.models.conversation import Conversation, Message
from app.api.v1.webhooks import _process_inbound_comment


@pytest_asyncio.fixture(autouse=True)
async def prepare_db():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_comment_to_dm_automation_flow():
    """Verify customer comment triggers DM with full price, color, and size details."""
    async with AsyncSessionLocal() as session:
        # Create product with color and size variants
        product = Product(
            sku="DRESS-COMMENT-01",
            product_name="Designer Party Dress",
            actual_price=500.0,
            selling_price=899.0,
            delivery_information="3-5 days delivery",
            cod_available=True
        )
        session.add(product)
        await session.commit()

        v1 = ProductVariant(product_id=product.product_id, type="color", value="Red", available=True)
        v2 = ProductVariant(product_id=product.product_id, type="color", value="Blue", available=True)
        v3 = ProductVariant(product_id=product.product_id, type="size", value="Medium", available=True)
        v4 = ProductVariant(product_id=product.product_id, type="size", value="Large", available=True)
        session.add_all([v1, v2, v3, v4])
        await session.commit()

        # Execute comment automation helper
        comment_id = "cmt_1001"
        media_id = "media_2002"
        from_user_id = "ig_commenter_001"
        comment_text = "price please?"

        await _process_inbound_comment(session, comment_id, media_id, from_user_id, comment_text)

        # Check created customer & conversation
        cust_res = await session.execute(select(Customer).where(Customer.instagram_user_id == from_user_id))
        customer = cust_res.scalars().first()
        assert customer is not None

        conv_res = await session.execute(select(Conversation).where(Conversation.customer_id == customer.customer_id))
        conv = conv_res.scalars().first()
        assert conv is not None

        # Check logged messages
        msg_res = await session.execute(select(Message).where(Message.conversation_id == conv.conversation_id))
        messages = msg_res.scalars().all()
        assert len(messages) == 2

        ai_dm = messages[1].message_text
        assert "Designer Party Dress" in ai_dm
        assert "899" in ai_dm
        assert "Red, Blue" in ai_dm
        assert "Medium, Large" in ai_dm
        assert "Please follow our page" in ai_dm
