# env_config.py

import os
from enum import Enum
from typing import Optional
from dotenv import load_dotenv

class Environment(Enum):
    PRODUCTION = "prod"
    DEVELOPMENT = "dev"
    TESTING = "test"

class DatabaseConfig:
    def __init__(self, environment: Environment):
        load_dotenv()
        
        self.environment = environment
        self._base_url = os.getenv('DATABASE_URL')
        if not self._base_url:
            raise ValueError("DATABASE_URL must be set in environment variables")

    @property
    def database_url(self) -> str:
        """
        Формирует URL базы данных в зависимости от окружения
        """
        if not self._base_url:
            raise ValueError("База данных не настроена")

        # Разбираем базовый URL
        if '?' in self._base_url:
            base, params = self._base_url.split('?')
        else:
            base = self._base_url
            params = ''

        # Добавляем суффикс к имени базы в зависимости от окружения
        if self.environment == Environment.DEVELOPMENT:
            base = base.replace('/motivaction_db', '/motivaction_dev_db')
        elif self.environment == Environment.TESTING:
            base = base.replace('/motivaction_db', '/motivaction_test_db')

        # Собираем URL обратно с параметрами
        return f"{base}{'?' + params if params else ''}"

    @property
    def schema_prefix(self) -> Optional[str]:
        """
        Возвращает префикс схемы для текущего окружения
        """
        if self.environment == Environment.DEVELOPMENT:
            return "dev_"
        elif self.environment == Environment.TESTING:
            return "test_"
        return None

def get_database_config(environment: Environment = Environment.PRODUCTION) -> DatabaseConfig:
    """
    Фабричный метод для получения конфигурации базы данных
    """
    return DatabaseConfig(environment)