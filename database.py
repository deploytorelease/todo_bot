# database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine
from config import DATABASE_URL
from models import Base
from contextlib import asynccontextmanager

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
async_sessionmaker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("База данных инициализирована")

@asynccontextmanager
async def get_db():
    async with async_sessionmaker() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def close_db():
    await engine.dispose()