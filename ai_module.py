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
    Во всех случаях возвращай даты и время в формате ISO 8601 (YYYY-MM-DDTHH:MM:SS).

    
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
            if not deadline:
                logging.warning(f"No deadline provided for {result['type']}. Using current date.")
                result['data']['deadline'] = datetime.now().isoformat() 
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
    
async def generate_goal_steps(goal_title: str, deadline: datetime, user_experience: str = None, available_time: str = None) -> dict:
    """
    Генерирует план достижения цели с учетом опыта пользователя и доступного времени
    """
    prompt = f"""
    Создай детальный план достижения цели "{goal_title}" до {deadline.strftime('%d.%m.%Y')}.
    План должен учитывать:
    - Уровень пользователя: {user_experience}
    - Доступное время: {available_time}
    
    Проанализируй цель и определи:
    1. Сложность каждого этапа (множитель от 0.5 до 2.0)
    2. Зависимости между этапами
    3. Оптимальное распределение времени
    
    Верни результат в формате JSON:
    {{
        "tasks": [
            {{
                "title": "название задачи",
                "description": "подробное описание",
                "complexity_factor": число от 0.5 до 2.0,
                "duration": количество_дней,
                "can_parallel": true/false,
                "deliverables": ["конкретные результаты"],
                "resources": ["материалы и инструменты"],
                "dependencies": []
            }}
        ],
        "milestones": [
            {{
                "title": "название этапа",
                "percentage": процент выполнения цели,
                "criteria": ["критерии успеха"]
            }}
        ]
    }}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional learning path designer."},
                {"role": "user", "content": prompt}
            ],
            response_format={ "type": "json_object" }
        )
        
        plan_data = json.loads(response.choices[0].message.content)
        
        # Распределяем задачи по времени
        current_date = datetime.now()
        scheduled_tasks = []
        
        for task in plan_data['tasks']:
            duration = task['duration']
            end_date = current_date + timedelta(days=duration)
            
            scheduled_task = {
                'title': task['title'],
                'description': task['description'],
                'start_date': current_date,
                'end_date': end_date,
                'deliverables': task.get('deliverables', []),
                'resources': task.get('resources', []),
                'dependencies': task.get('dependencies', []),
                'can_parallel': task.get('can_parallel', False)
            }
            
            scheduled_tasks.append(scheduled_task)
            if not task.get('can_parallel', False):
                current_date = end_date
        
        return {
            'tasks': scheduled_tasks,
            'milestones': [
                {
                    'title': 'Промежуточная проверка',
                    'date': deadline - timedelta(days=deadline.day//2),
                    'criteria': ['Выполнено 50% задач', 'Созданы базовые проекты']
                },
                {
                    'title': 'Финальная проверка',
                    'date': deadline,
                    'criteria': ['Выполнены все задачи', 'Достигнуты все цели обучения']
                }
            ]
        }
            
    except Exception as e:
        logger.error(f"Ошибка при генерации плана: {e}")
        return {
            'tasks': [],
            'milestones': []
        }