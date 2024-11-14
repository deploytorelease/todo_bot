from datetime import datetime, timedelta


def optimize_task_schedule(tasks: list, deadline: datetime) -> list:
    """
    Оптимизирует расписание задач с учетом возможности параллельного выполнения
    """
    # Создаем граф зависимостей
    dependency_graph = {}
    for task in tasks:
        task_id = task['title']
        dependency_graph[task_id] = {
            'dependencies': task['dependencies'],
            'duration': task['duration'],
            'can_parallel': task['can_parallel']
        }
    
    # Находим критический путь
    critical_path = find_critical_path(dependency_graph)
    
    # Распределяем задачи по времени
    schedule = []
    current_date = datetime.now()
    
    for task in tasks:
        if task['title'] in critical_path:
            # Задачи критического пути выполняются последовательно
            task['start_date'] = current_date
            task['end_date'] = current_date + timedelta(days=task['duration'])
            current_date = task['end_date']
        elif task['can_parallel']:
            # Параллельные задачи можно начать раньше
            task['start_date'] = find_earliest_start(task, schedule)
            task['end_date'] = task['start_date'] + timedelta(days=task['duration'])
        
        schedule.append(task)
    
    return schedule

def find_critical_path(graph: dict) -> list:
    """
    Находит критический путь в графе зависимостей задач
    """
    # Реализация алгоритма поиска критического пути
    # Возвращает список задач, которые должны выполняться последовательно
    pass

def find_earliest_start(task: dict, schedule: list) -> datetime:
    """
    Находит самое раннее возможное время начала задачи с учетом зависимостей
    """
    # Реализация поиска раннего старта
    # Учитывает зависимости и возможность параллельного выполнения
    pass

def get_tasks_for_milestone(schedule: list, milestone_date: str) -> list:
    """
    Определяет список задач, которые должны быть завершены к определенной контрольной точке
    """
    milestone_datetime = datetime.fromisoformat(milestone_date)
    return [
        task['title'] for task in schedule 
        if task['end_date'] <= milestone_datetime
    ]
