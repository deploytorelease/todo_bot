# ai_module.py

from openai import OpenAI
from config import OPENAI_API_KEY
from datetime import datetime, timedelta
import logging
import json
import re

client = OpenAI(api_key=OPENAI_API_KEY)

async def parse_message(message_text: str):
    current_time = datetime.now().isoformat()
    prompt = f"""
    Проанализируй следующий текст и извлеки из него информацию о задачах, финансах или целях. 
    Верни результат в формате JSON со следующей структурой:
    {{
        "type": "task" или "finance" или "goal" или "clarification",
        "data": {{
            // Для задачи:
            "title": "Название задачи",
            "due_date": "YYYY-MM-DDTHH:MM:SS",
            "priority": "high" или "medium" или "low",
            "category": "Категория задачи"
            
            // Для финансов:
            "amount": числовое значение,
            "category": "Категория траты",
            "description": "Описание траты"
            
            // Для цели:
            "title": "Название цели",
            "deadline": "ДД.ММ.ГГГГ",
            "steps": ["Шаг 1", "Шаг 2", ...]

            // Для уточнения:
            "task_number": числовое значение
        }}
    }}
    
    Текущее время: {current_time}
    Используй текущее время как отправную точку для расчета времени задачи.
    Если указано относительное время (например, "через 2 минуты"), рассчитай точное время от текущего момента.
    
    Текст для анализа: '{message_text}'
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that parses text and extracts structured information."},
                {"role": "user", "content": prompt}
            ]
        )

        content = response.choices[0].message.content.strip()
        
        # Извлекаем JSON из ответа, даже если он обернут в тройные обратные кавычки
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
        else:
            json_str = content

        result = json.loads(json_str)
        logging.info(f"Parsed message: {result}")

        # Обработка даты для задач
        if result['type'] == 'task' and 'due_date' in result['data']:
            due_date = result['data']['due_date']
            if 'следующие выходные' in message_text.lower():
                # Находим дату следующей субботы
                today = datetime.now()
                next_saturday = today + timedelta((5 - today.weekday() + 7) % 7)
                result['data']['due_date'] = next_saturday.strftime('%d.%m.%Y 23:59')

        # Обработка уточнения
        if result['type'] == 'clarification' and 'task_number' in result['data']:
            return {"type": "clarification", "data": {"task_number": result['data']['task_number']}}

        return result
    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse JSON from API response: {content}")
        return {"type": "unknown", "data": {}}
    except Exception as e:
        logging.error(f"Error parsing message: {e}")
        return {"type": "unknown", "data": {}}
    

async def parse_clarification(clarification_prompt: str):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that clarifies user intentions."},
                {"role": "user", "content": clarification_prompt}
            ]
        )

        content = response.choices[0].message.content.strip()
        
        # Извлекаем номер задачи из ответа
        task_number_match = re.search(r'\d+', content)
        if task_number_match:
            return {"type": "clarification", "data": {"task_number": int(task_number_match.group())}}
        else:
            return {"type": "unknown", "data": {}}
    except Exception as e:
        logging.error(f"Error parsing clarification: {e}")
        return {"type": "unknown", "data": {}}

async def generate_personalized_message(user, message_type, **kwargs):
    tone = user.tone if hasattr(user, 'tone') else 'neutral'
    role = user.role if hasattr(user, 'role') else 'assistant'

    prompt = f"Выступая в роли {role} и используя {tone} тон общения, "

    if message_type == 'reminder':
        task_title = kwargs.get('task_title')
        is_overdue = kwargs.get('is_overdue', False)
        if is_overdue:
            prompt += f"мотивируй пользователя выполнить просроченную задачу '{task_title}'."
        else:
            prompt += f"напомни пользователю о задаче '{task_title}' и мотивируй его выполнить ее."
    elif message_type == 'motivation':
        prompt += "предоставь пользователю мотивационное сообщение, чтобы помочь ему справиться с прокрастинацией."
    elif message_type == 'learning_plan':
        topic = kwargs.get('topic')
        prompt += f"составь план обучения по теме '{topic}' с конкретными шагами на каждый день в течение недели."
    elif message_type == 'learning_progress':
        progress = kwargs.get('progress')
        prompt += f"спроси пользователя о его успехах в изучении темы и предложи дальнейшие действия."
    elif message_type == 'financial_advice':
        recent_expenses = kwargs.get('recent_expenses')
        prompt += f"дай совет по экономии, основываясь на последних тратах пользователя: {recent_expenses}"
    elif message_type == 'goal_planning':
        goal_title = kwargs.get('goal_title')
        prompt += f"помоги спланировать достижение цели '{goal_title}' с конкретными шагами."
    elif message_type == 'learning_resources':
        topic = kwargs.get('topic')
        prompt += f"предложи полезные ресурсы для изучения темы '{topic}', включая книги, онлайн-курсы и практические задания."
    else:
        logging.error("Неизвестный тип сообщения.")
        return "Ошибка: неизвестный тип сообщения."

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=250,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI API: {e}")
        return "Извините, произошла ошибка при генерации сообщения."