from typing import List, Dict, Optional
from datetime import timedelta
from models import Task
import json
from datetime import datetime



def get_task_context(tasks_history, current_task):
    """
    Анализирует контекст задач пользователя для более релевантных сообщений
    """
    context = {
        'total_tasks': len(tasks_history),
        'completed_rate': sum(1 for t in tasks_history if t.is_completed) / len(tasks_history) if tasks_history else 0,
        'common_postpone_reasons': [t.postpone_reason for t in tasks_history if t.postpone_reason],
        'preferred_completion_time': analyze_completion_patterns(tasks_history),
        'task_complexity': estimate_task_complexity(current_task),
        'similar_tasks': find_similar_completed_tasks(tasks_history, current_task)
    }
    return context

async def find_similar_completed_tasks(tasks_history: List[Task], current_task: Task) -> List[Dict]:
    """Находит похожие завершенные задачи"""
    similar_tasks = []
    
    # Получаем ключевые слова из текущей задачи
    current_keywords = set(extract_keywords(current_task.title + " " + (current_task.description or "")))
    
    for task in tasks_history:
        if not task.is_completed:
            continue
            
        # Получаем ключевые слова из исторической задачи
        task_keywords = set(extract_keywords(task.title + " " + (task.description or "")))
        
        # Вычисляем схожесть
        similarity = len(current_keywords.intersection(task_keywords)) / len(current_keywords.union(task_keywords))
        
        if similarity >= 0.3:  # Порог схожести
            similar_tasks.append({
                "task": task,
                "similarity": similarity,
                "completion_time": task.completion_date - task.created_at if task.completion_date else None
            })
    
    # Сортируем по схожести
    similar_tasks.sort(key=lambda x: x["similarity"], reverse=True)
    return similar_tasks[:3]  # Возвращаем топ-3 похожие задачи

def extract_keywords(text: str) -> List[str]:
    """Извлекает ключевые слова из текста"""
    # Простая реализация - разбиваем на слова и фильтруем стоп-слова
    stop_words = {'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все', 'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по', 'только', 'ее', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из', 'ему'}
    return [word.lower() for word in text.split() if word.lower() not in stop_words]

def analyze_completion_patterns(tasks_history):
    """
    Определяет наиболее продуктивное время пользователя
    """
    completion_times = [
        task.completion_date.hour 
        for task in tasks_history 
        if task.is_completed and task.completion_date
    ]
    
    if not completion_times:
        return None
        
    from collections import Counter
    time_counter = Counter(completion_times)
    peak_hour = max(time_counter.items(), key=lambda x: x[1])[0]
    
    return {
        'peak_hour': peak_hour,
        'morning_rate': sum(1 for h in completion_times if 5 <= h < 12) / len(completion_times),
        'afternoon_rate': sum(1 for h in completion_times if 12 <= h < 17) / len(completion_times),
        'evening_rate': sum(1 for h in completion_times if 17 <= h < 22) / len(completion_times)
    }


def estimate_task_complexity(task: Task) -> int:
    """Оценивает сложность задачи по шкале от 1 до 5"""
    complexity_score = 1

    # Учитываем длину описания
    if task.description:
        if len(task.description) > 500:
            complexity_score += 1
        if len(task.description) > 1000:
            complexity_score += 1

    # Учитываем срок выполнения
    if task.due_date:
        time_until_due = task.due_date - datetime.now()
        if time_until_due.days < 1:
            complexity_score += 1
        elif time_until_due.days > 7:
            complexity_score -= 1

    # Учитываем зависимости
    if task.dependencies:
        dependencies = json.loads(task.dependencies)
        complexity_score += min(len(dependencies), 2)

    # Нормализуем оценку
    return min(max(complexity_score, 1), 5)

def analyze_productivity_hours(completion_times: List[int]) -> List[int]:
    """Анализирует самые продуктивные часы на основе времени завершения задач"""
    if not completion_times:
        return []
        
    from collections import Counter
    hour_counter = Counter(completion_times)
    
    # Находим часы с наибольшим количеством завершенных задач
    average_completions = sum(hour_counter.values()) / len(hour_counter)
    productive_hours = [
        hour for hour, count in hour_counter.items()
        if count > average_completions
    ]
    
    return sorted(productive_hours)

def calculate_completion_rate(completed_tasks: List[Task], active_tasks: List[Task]) -> float:
    """Рассчитывает процент завершения задач"""
    total_tasks = len(completed_tasks) + len(active_tasks)
    if total_tasks == 0:
        return 0.0
    return (len(completed_tasks) / total_tasks) * 100

def calculate_average_task_time(completed_tasks: List[Task]) -> Optional[timedelta]:
    """Рассчитывает среднее время выполнения задач"""
    if not completed_tasks:
        return None
        
    completion_times = [
        task.completion_date - task.created_at
        for task in completed_tasks
        if task.completion_date and task.created_at
    ]
    
    if not completion_times:
        return None
        
    return sum(completion_times, timedelta()) / len(completion_times)

def analyze_task_complexity(tasks: List[Task]) -> Dict[str, int]:
    """Анализирует распределение сложности задач"""
    complexity_dist = {
        "low": 0,
        "medium": 0,
        "high": 0
    }
    
    for task in tasks:
        complexity = estimate_task_complexity(task)
        if complexity <= 2:
            complexity_dist["low"] += 1
        elif complexity <= 4:
            complexity_dist["medium"] += 1
        else:
            complexity_dist["high"] += 1
            
    return complexity_dist

def calculate_on_time_rate(completed_tasks: List[Task]) -> float:
    """Рассчитывает процент задач, выполненных в срок"""
    if not completed_tasks:
        return 0.0
        
    on_time = sum(
        1 for task in completed_tasks
        if task.completion_date and task.due_date and task.completion_date <= task.due_date
    )
    
    return (on_time / len(completed_tasks)) * 100