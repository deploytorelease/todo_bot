# config.py

import os
from pathlib import Path
from dotenv import load_dotenv
from enum import Enum

class Environment(Enum):
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"
    TESTING = "test"

def load_environment_config():
    """
    Загружает конфигурацию в зависимости от окружения
    """
    # Определяем текущее окружение из ENV или используем development по умолчанию
    """
    env_name = os.getenv('APP_ENV', 'development')
    """
    env_name = os.getenv('ENVIRONMENT', 'prod')
    
    # Определяем путь к файлу конфигурации
    env_file = f".env.{env_name}"
    
    # Проверяем существование файла
    if not Path(env_file).exists():
        print(f"Warning: {env_file} not found, falling back to .env")
        env_file = ".env"
    
    # Загружаем конфигурацию
    load_dotenv(env_file, override=True)
    
    return Environment(os.getenv('ENVIRONMENT', 'prod'))

# Загружаем конфигурацию
ENVIRONMENT = load_environment_config()

# Получаем переменные окружения
BOT_TOKEN = os.getenv('BOT_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DATABASE_URL = os.getenv('DATABASE_URL')

# Проверяем обязательные переменные
if not all([BOT_TOKEN, OPENAI_API_KEY, DATABASE_URL]):
    raise ValueError("Missing required environment variables. Check your .env file.")

def get_database_name():
    """
    Получает имя базы данных в зависимости от окружения
    """
    if ENVIRONMENT == Environment.DEVELOPMENT:
        return "tasks_dev"
    elif ENVIRONMENT == Environment.TESTING:
        return "tasks_test"
    return "tasks"

def get_full_database_url():
    """
    Формирует полный URL базы данных с учетом окружения
    """
    # Получаем базовый URL без имени базы
    base_url = DATABASE_URL.rsplit('/', 1)[0]
    # Добавляем нужное имя базы
    return f"{base_url}/{get_database_name()}"

# Финальный URL базы данных
DATABASE_URL = get_full_database_url()