# ai_module.py

from openai import OpenAI
from config import OPENAI_API_KEY
from datetime import datetime, timedelta
import logging
import json
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

client = OpenAI(api_key=OPENAI_API_KEY)

def parse_date(date_string):
    date_formats = ['%Y-%m-%d', '%d.%m.%Y', '%m/%d/%Y', '%Y/%m/%d', '%Y-%m-%dT%H:%M:%S']
    for fmt in date_formats:
        try:
            return datetime.strptime(date_string, fmt).strftime('%Y-%m-%d %H:%M:%S')
        except ValueError:
            continue
    raise ValueError(f"Неподдерживаемый формат даты: {date_string}")

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
            "currency": "USD" или "EUR" или "RUB" и т.д.,
            "category": "Категория транзакции",
            "description": "Описание транзакции",
            "type": "income" или "expense" или "savings" или "regular_payment",
            "frequency": "monthly" или "quarterly" или "annually" (только для regular_payment),
            "next_payment_date": "YYYY-MM-DD" (только для regular_payment)
            
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
    Если пользователь не указал срок для цели, предложи разумный срок исходя из сложности цели.
    Для изучения языка программирования, например, можно предложить срок от 3 до 6 месяцев.
    - Для чтения книги - от нескольких дней до месяца, в зависимости от объема.
    - Для сложных долгосрочных целей - до года или более.
    Если указан срок в формате "через Х дней", рассчитай дату исходя из текущей даты.
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
        if result['type'] in ['task', 'goal']:
            deadline = result['data'].get('deadline') or result['data'].get('due_date')
            if deadline:
                try:
                    result['data']['deadline'] = parse_date(deadline)
                except ValueError as e:
                    logging.error(f"Failed to parse date: {e}")
                    result['data']['deadline'] = datetime.now().strftime('%Y-%m-%d')
            else:
                logging.warning(f"No deadline provided for {result['type']}. Using current date.")
                result['data']['deadline'] = datetime.now().strftime('%Y-%m-%d')

        if result['type'] == 'finance':
            if 'currency' not in result['data']:
                result['data']['currency'] = 'USD'  # Устанавливаем значение по умолчанию, если валюта не указана
            if 'type' not in result['data']:
                result['data']['type'] = 'expense'  # По умолчанию считаем операцию расходом
            if result['data']['type'] == 'regular_payment' and 'frequency' not in result['data']:
                result['data']['frequency'] = 'monthly'  # Устанавливаем месячную частоту по умолчанию


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
    
    
async def analyze_expenses(expense_data, income_data):
    prompt = f"""
    Проанализируй следующие данные о расходах и доходах за последнюю неделю:

    Расходы:
    {json.dumps(expense_data, indent=2)}

    Доходы:
    {json.dumps(income_data, indent=2)}

    Предоставь анализ финансов, фокусируясь на следующих аспектах:
    1. Общая сумма доходов и расходов
    2. Баланс (разница между доходами и расходами)
    3. Основные категории расходов
    4. Сравнение расходов с доходами
    5. Выявление потенциально необязательных или избыточных расходов
    6. Анализ сбережений (если есть)
    7. Предложения по оптимизации расходов и увеличению сбережений
    8. Сравнение с типичными расходами (если возможно)

    Не предлагай радикальных мер, таких как смена жилья или работы. 
    Сосредоточься на небольших, но эффективных изменениях в расходах.
    Будь тактичным и мотивирующим в своих рекомендациях.
    Учитывай разные валюты в анализе.

    Представь анализ в виде структурированного текста, удобного для чтения в мессенджере.
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a helpful financial advisor."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000,
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        logger.error(f"Ошибка при анализе расходов: {e}", exc_info=True)
        return "Извините, произошла ошибка при анализе расходов. Пожалуйста, попробуйте позже."

async def generate_personalized_message(user, message_type, **kwargs):
    logger.info(f"Генерация персонализированного сообщения для пользователя {user.user_id}, тип: {message_type}")
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
        logger.info(f"Получено сообщение от OpenAI API: {response.choices[0].message.content.strip()}")
        return response.choices[0].message.content.strip()
    except Exception as e:
        logging.error(f"Ошибка при обращении к OpenAI API: {e}")
        return "Извините, произошла ошибка при генерации сообщения."