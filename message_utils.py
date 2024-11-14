from database import get_db
from models import User, Task
from ai_module import client  # Импортируем OpenAI клиент
from user_context import get_user_context
import logging
from datetime import datetime
from typing import Optional, Dict, Any
import json

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def get_user(user_id):
    async with get_db() as session:
        return await session.get(User, user_id)

async def get_task(task_id):
    async with get_db() as session:
        return await session.get(Task, task_id)

async def analyze_user_message(prompt: str) -> Dict[str, Any]:
    """Анализирует сообщение пользователя и возвращает структурированный результат"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that analyzes user messages."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        logger.error(f"Ошибка при анализе сообщения: {e}")
        return {
            "intent": "unknown",
            "emotion": "neutral",
            "needs_support": False,
            "action_items": []
        }

async def generate_message(user_id: int, message_type: str, use_context: bool = True, **kwargs) -> str:
    """
    Универсальная функция для генерации персонализированных сообщений.
    
    Args:
        user_id: ID пользователя
        message_type: Тип сообщения
        use_context: Использовать ли расширенный контекст пользователя
        **kwargs: Дополнительные параметры для сообщения
    """
    try:
        user = await get_user(user_id)
        if not user:
            return "Пользователь не найден"
        user_tone = user.tone if user.tone else 'neutral'
        # Получаем базовый контекст
        base_context = f"""
        Роль: эмпатичный коуч-ассистент, помогающий достигать целей
        История взаимодействий: {kwargs.get('interaction_history', [])}
        Текущее время суток: {datetime.now().strftime('%H:%M')}
        """

        # Если требуется расширенный контекст, добавляем его
        if use_context:
            user_context = await get_user_context(user_id)
            base_context += f"""
            Загрузка: {user_context['task_context']['workload_level']}
            Уровень стресса: {user_context['emotional_context']['stress_level']}
            Активных задач: {user_context['task_context']['active_tasks']}
            Стиль общения: {user_context['metrics']['interaction_style']}
            Продуктивные часы: {', '.join(map(str, user_context['metrics']['preferred_hours']))}
            """

        # Словарь промптов для разных типов сообщений
        prompts = {
            'task_reminder_regular': f"""
                {base_context}
                Задача: {kwargs.get('task_title')}
                Срок: {kwargs.get('due_date')}
                
                Создай краткое, мотивирующее напоминание о задаче. Учитывай:
                - Если это первое напоминание, будь более информативным
                - При повторных напоминаниях меняй формулировки
                Напоминание должно быть кратким (до 2 предложений)
            """,
            'task_reminder_urgent': f"""
                {base_context}
                Задача: {kwargs.get('task_title')}
                Срок: {kwargs.get('due_date')}
                
                Задача скоро истекает! Создай срочное напоминание, подчеркивающее важность выполнения.
            """,
            'task_reminder_overdue': f"""
                {base_context}
                Задача: {kwargs.get('task_title')}
                Просрочено на: {kwargs.get('overdue_time')}
                
                Создай поддерживающее напоминание о просроченной задаче. Учитывай:
                - Вырази понимание
                - Предложи помощь в планировании
            """,
            'daily_summary': f"""
                {base_context}
                Задачи на сегодня: {kwargs.get('today_tasks', [])}
                Выполнено вчера: {kwargs.get('completed_yesterday', [])}
                
                Создай краткий обзор дня, где:
                - Отметь главные приоритеты (не более 3)
                - Если есть успехи вчера - кратко похвали
                - При большой загрузке предложи что можно отложить
                - Если задач мало - поддержи и предложи подумать о целях
            """,
            'goal_progress': f"""
                {base_context}
                Цель: {kwargs.get('goal_title')}
                Прогресс: {kwargs.get('progress')}%
                Последнее действие: {kwargs.get('last_action')}
                
                Создай поддерживающее сообщение о прогрессе:
                - Отметь конкретное достижение
                - Предложи следующий небольшой шаг
                - При замедлении прогресса деликатно уточни о сложностях
            """,
            'workload_management': f"""
                {base_context}
                Предстоящие дедлайны: {kwargs.get('upcoming_deadlines', [])}
                
                Создай сообщение об управлении нагрузкой:
                - Учти текущий уровень стресса
                - Предложи конкретные шаги по приоритизации
                - Напомни о важности отдыха
            """,
            'support_message': f"""
                {base_context}
                Текущие сложности: {kwargs.get('current_challenges', [])}
                
                Создай поддерживающее сообщение:
                - Учти текущий уровень стресса
                - Используй опыт успешного решения похожих задач
                - Предложи конкретные шаги
            """
        }

        # Получаем нужный промпт или используем базовый контекст
        prompt = prompts.get(message_type, base_context + "\nСоздай уместное сообщение для текущей ситуации.")
        logger.info(f"message_type: {message_type}")
        logger.info(f"Generated prompt: {prompt}")
        # Генерируем сообщение через OpenAI API
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": f"Ты эмпатичный ассистент, который помогает пользователям достигать целей.Твой тон общения должен быть {user_tone}"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        logger.info(f"API response: {response}")
        return response.choices[0].message.content.strip()

    except Exception as e:
        logger.error(f"Ошибка при генерации сообщения: {e}")
        return "Давайте обсудим, как я могу помочь вам с текущей задачей."

async def send_personalized_message(bot, user_id, message_type, **kwargs):
    """
    Отправляет персонализированное сообщение пользователю
    """
    try:
        message = await generate_message(user_id, message_type, **kwargs)
        await bot.send_message(chat_id=user_id, text=message)
        return True
    except Exception as e:
        logger.error(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")
        return False