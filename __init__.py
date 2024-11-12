# __init__.py

"""
MotivAction Bot - Проактивный ИИ-коуч для достижения целей
"""

from .config import BOT_TOKEN, OPENAI_API_KEY, DATABASE_URL
from .database import init_db, get_db, close_db
from .models import (
    User, Task, TaskCategory, FinancialRecord, 
    RegularPayment, Goal, ReminderEffectiveness
)
from .scheduler import start_scheduler
from .ai_module import generate_personalized_message, analyze_expenses

__version__ = '1.0.0'
__author__ = 'Your Name'
__email__ = 'your.email@example.com'

# Константы для всего приложения
DEFAULT_REMINDER_INTERVAL = 30  # минут
MAX_REMINDERS_PER_TASK = 5
QUIET_HOURS_START = 23  # часы
QUIET_HOURS_END = 7    # часы

# Типы сообщений
MESSAGE_TYPES = {
    'task_reminder': 'Напоминание о задаче',
    'daily_summary': 'Ежедневная сводка',
    'overdue': 'Просроченная задача',
    'motivation': 'Мотивационное сообщение',
    'financial_report': 'Финансовый отчет'
}

# Категории задач по умолчанию
DEFAULT_TASK_CATEGORIES = [
    ('Срочное', 100, '#FF4444'),
    ('Работа', 90, '#4444FF'),
    ('Учёба', 80, '#44FF44'),
    ('Здоровье', 85, '#44FFFF'),
    ('Финансы', 75, '#FFFF44'),
    ('Личное', 70, '#FF44FF'),
    ('Покупки', 60, '#FFA500'),
    ('Дом', 65, '#8B4513'),
    ('Хобби', 50, '#9370DB'),
    ('Разное', 0, '#808080')
]

def get_version():
    """Возвращает текущую версию бота"""
    return __version__

def get_task_category_info():
    """Возвращает информацию о категориях задач"""
    return {name: {'priority': priority, 'color': color} 
            for name, priority, color in DEFAULT_TASK_CATEGORIES}