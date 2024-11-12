# database.py

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import AsyncEngine
from config import DATABASE_URL
from models import Base
from contextlib import asynccontextmanager
import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

engine: AsyncEngine = create_async_engine(DATABASE_URL, echo=False)
async_sessionmaker = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Инициализация базы данных без удаления существующих данных"""
    try:
        # Только создаем таблицы, если их нет
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {e}")
        raise

@asynccontextmanager
async def get_db():
    for attempt in range(3):  # Попытаемся подключиться 3 раза
        try:
            async with async_sessionmaker() as session:
                try:
                    yield session
                    await session.commit()
                except Exception:
                    await session.rollback()
                    raise
                finally:
                    await session.close()
            break  # Если успешно подключились и выполнили операции, выходим из цикла
        except Exception as e:
            if attempt == 2:  # Если это была последняя попытка
                logger.error(f"Не удалось подключиться к базе данных после 3 попыток: {e}")
                raise
            logger.warning(f"Ошибка подключения к базе данных, попытка {attempt + 1}: {e}")
            await asyncio.sleep(1)  # Подождем секунду перед следующей попыткой

async def close_db():
    await engine.dispose()

# Дополнительная функция для очистки базы (использовать только для тестов)
async def clear_db():
    """ВНИМАНИЕ: Использовать только для тестов!
    Удаляет все данные из базы данных."""
    if 'test' not in DATABASE_URL.lower():
        raise RuntimeError("Очистка базы данных разрешена только для тестовой базы")
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)