# message_generation.py

from openai import OpenAI
from config import OPENAI_API_KEY
import logging
from typing import Dict, Any
import json

client = OpenAI(api_key=OPENAI_API_KEY)
logger = logging.getLogger(__name__)

async def generate_message(prompt: str) -> str:
    """Генерирует сообщение для диалога используя OpenAI API"""
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": "Ты эмпатичный ассистент, который помогает пользователям достигать целей."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=150
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка при генерации сообщения: {e}")
        return "Давайте продолжим нашу работу. Как я могу помочь?"

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