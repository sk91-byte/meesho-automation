import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app
from app.core.database import AsyncSessionLocal, async_engine, Base
from app.core.security import get_password_hash, create_access_token
from app.models.user import User, RoleEnum

owner_user_id = None


@pytest_asyncio.fixture(autouse=True)
async def prepare_database():
    global owner_user_id
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with AsyncSessionLocal() as session:
        user = User(
            email="owner@meesho.store",
            hashed_password=get_password_hash("Owner123!"),
            full_name="Business Owner",
            role=RoleEnum.OWNER,
            is_active=True
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        owner_user_id = user.user_id

    yield

    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_create_and_list_product():
    global owner_user_id
    token = create_access_token(subject=owner_user_id, extra_claims={"role": "OWNER"})
    headers = {"Authorization": f"Bearer {token}"}
    
    product_payload = {
        "sku": "PROD-BAG-001",
        "product_name": "Women's Sling Bag",
        "description": "Stylish PU leather bag",
        "actual_price": 299.0,
        "selling_price": 449.0,
        "currency": "INR",
        "meesho_url": "https://meesho.com/s/p/abc12",
        "variants": [
            {"type": "color", "value": "Black", "available": True},
            {"type": "color", "value": "Pink", "available": False}
        ],
        "faqs": [
            {"question": "Is COD available?", "answer": "Yes, COD is available.", "verified_by_owner": True}
        ]
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create product
        res = await client.post("/api/v1/products/", json=product_payload, headers=headers)
        assert res.status_code == 201
        data = res.json()
        assert data["sku"] == "PROD-BAG-001"
        assert data["actual_price"] == 299.0
        assert data["selling_price"] == 449.0
        assert len(data["variants"]) == 2
        assert len(data["faqs"]) == 1
        product_id = data["product_id"]

        # Get product by ID
        res_get = await client.get(f"/api/v1/products/{product_id}")
        assert res_get.status_code == 200
        assert res_get.json()["product_name"] == "Women's Sling Bag"

        # List products
        res_list = await client.get("/api/v1/products/")
        assert res_list.status_code == 200
        assert len(res_list.json()) == 1
