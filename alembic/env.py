import os
from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from dotenv import load_dotenv
import sys
from pathlib import Path

# Добавляем корневую директорию проекта в PYTHONPATH
sys.path.append(str(Path(__file__).parent.parent))

# Загружаем переменные окружения
load_dotenv()

# Получаем конфиг Alembic
config = context.config

# Загружаем конфигурацию логирования из alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Получаем URL базы данных из переменной окружения
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL must be set in environment variables")

# Заменяем asyncpg на psycopg2 для Alembic
SQLALCHEMY_DATABASE_URL = DATABASE_URL.replace("postgresql+asyncpg", "postgresql")

# Устанавливаем URL в конфигурацию
config.set_main_option("sqlalchemy.url", SQLALCHEMY_DATABASE_URL)

# Импортируем метаданные моделей
from base import Base
# Импортируем все модели, чтобы они были зарегистрированы в метаданных
from models import *

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()