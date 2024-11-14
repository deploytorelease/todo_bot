from datetime import datetime, timedelta


def generate_checkpoints(schedule: list, total_duration: timedelta) -> list:
    """
    Генерирует промежуточные точки проверки прогресса
    """
    start_date = datetime.now()
    mid_date = start_date + (total_duration / 2)
    end_date = start_date + total_duration

    return [
        {
            'title': 'Промежуточная проверка',
            'date': mid_date,
            'criteria': ['Выполнено 50% задач', 'Созданы базовые проекты']
        },
        {
            'title': 'Финальная проверка',
            'date': end_date,
            'criteria': ['Выполнены все задачи', 'Достигнуты все цели обучения']
        }
    ]