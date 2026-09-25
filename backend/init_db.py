import asyncio
from sqlalchemy.future import select
from app.core.database import AsyncSessionLocal, async_engine, Base
from app.core.security import get_password_hash
from app.models.user import User, RoleEnum
from app.core.logging import logger, setup_logging

setup_logging()


async def seed_initial_data():
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSessionLocal() as session:
        result = await session.execute(select(User).where(User.email == "owner@meesho.store"))
        existing_owner = result.scalars().first()
        if not existing_owner:
            owner = User(
                email="owner@meesho.store",
                hashed_password=get_password_hash("Owner123!"),
                full_name="Business Owner",
                role=RoleEnum.OWNER,
                is_active=True
            )
            session.add(owner)
            await session.commit()
            logger.info("Successfully seeded default owner account: owner@meesho.store")
        else:
            logger.info("Default owner account already exists.")


if __name__ == "__main__":
    asyncio.run(seed_initial_data())
