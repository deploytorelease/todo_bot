# MotivAction Bot

Проактивный ИИ-коуч Telegram бот для достижения целей и личностного роста.

## Структура проекта

```
motivaction/
├── __init__.py
├── main.py               # Точка входа приложения
├── config.py            # Конфигурация и переменные окружения
├── database.py          # Настройка и управление базой данных
├── models.py            # SQLAlchemy модели
├── handlers.py          # Обработчики команд бота
├── scheduler.py         # Планировщик задач и напоминаний
├── ai_module.py         # Интеграция с GPT и обработка текста
├── message_utils.py     # Утилиты для работы с сообщениями
├── tone.py             # Управление тоном общения
├── tests/              # Директория с тестами
│   ├── __init__.py
│   ├── utils.py
│   └── test_scheduler.py
├── requirements.txt     # Основные зависимости
└── requirements-test.txt # Зависимости для тестирования
```

## Технологии

- Python 3.9+
- aiogram 3.x (Telegram Bot API)
- SQLAlchemy (ORM)
- PostgreSQL (База данных)
- OpenAI GPT-4 (ИИ компонент)
- APScheduler (Планировщик задач)

## База данных

### Основные таблицы:
1. users - Пользователи и их настройки
2. tasks - Задачи пользователей
3. task_categories - Категории задач
4. financial_records - Финансовые записи
5. regular_payments - Регулярные платежи
6. goals - Цели пользователей
7. reminder_effectiveness - Статистика эффективности напоминаний

Полная схема базы данных находится в [DATABASE.md](database_schema.md)

## Основные функции

1. Управление задачами:
   - Создание и отслеживание задач
   - Умные напоминания
   - Категоризация
   - Приоритизация

2. Финансовый трекинг:
   - Учет доходов и расходов
   - Регулярные платежи
   - Аналитика расходов

3. Постановка и достижение целей:
   - Разбивка целей на подзадачи
   - Отслеживание прогресса
   - Контрольные точки

4. Проактивное взаимодействие:
   - Умные напоминания
   - Мотивационные сообщения
   - Адаптивные интервалы уведомлений

## Установка и запуск

1. Клонируйте репозиторий:
```bash
git clone https://github.com/yourusername/motivaction-bot.git
cd motivaction-bot
```

2. Создайте виртуальное окружение:
```bash
python -m venv venv
source venv/bin/activate  # Linux/MacOS
venv\Scripts\activate     # Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Создайте файл .env:
```env
BOT_TOKEN=your_telegram_bot_token
OPENAI_API_KEY=your_openai_api_key
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/motivaction_db
```

5. Создайте базу данных:
```sql
CREATE DATABASE motivaction_db;
```

6. Запустите бота:
```bash
python main.py
```

## Тестирование

1. Создайте тестовую базу данных:
```sql
CREATE DATABASE test_motivaction_db;
```

2. Установите зависимости для тестов:
```bash
pip install -r requirements-test.txt
```

3. Запустите тесты:
```bash
pytest
```

## Развертывание

Бот развернут на сервере с использованием Docker. Инструкции по развертыванию находятся в [DEPLOYMENT.md](deployment.md)

## Документация

- [API документация](api.md)
- [Схема базы данных](database_schema.md)
- [Инструкция по развертыванию](deployment.md)
- [Разработка новых функций](development.md)