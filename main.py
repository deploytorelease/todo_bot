# main.py

import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from config import BOT_TOKEN
from handlers import register_handlers
from scheduler import start_scheduler
from database import init_db, close_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def main():
    # Инициализация базы данных
    await init_db()
    
    # Инициализация бота и диспетчера
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Регистрация обработчиков
    register_handlers(dp)
    
    # Запуск планировщика
    scheduler = start_scheduler(bot)
    
    try:
        # Запуск бота
        await dp.start_polling(bot)
    except Exception as e:
        logger.exception(f"Произошла ошибка: {e}")
    finally:
        # Корректное завершение работы
        await bot.session.close()
        await close_db()

if __name__ == '__main__':
    asyncio.run(main())