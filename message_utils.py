from database import get_db
from models import User, Task
from ai_module import generate_personalized_message
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_user(user_id):
    async with get_db() as session:
        return await session.get(User, user_id)

async def get_task(task_id):
    async with get_db() as session:
        return await session.get(Task, task_id)

async def send_personalized_message(bot, user_id, message_type, **kwargs):
    user = await get_user(user_id)
    message = await generate_personalized_message(user, message_type, **kwargs)
    try:
        if bot:
            await bot.send_message(chat_id=user_id, text=message)
            logger.info(f"Сообщение успешно отправлено пользователю {user_id}")
        else:
            logger.warning(f"Бот не предоставлен, сообщение не отправлено пользователю {user_id}")
        return message
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return message