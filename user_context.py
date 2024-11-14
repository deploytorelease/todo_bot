from datetime import datetime, timedelta
from typing import List, Dict, Any
from database import get_db
from sqlalchemy import select
from models import (
    User, 
    Task, 
    UserInteractionMetrics,
    DialogEmotionalState,
    EmotionalState
)
import logging

logger = logging.getLogger(__name__)

async def get_user_context(user_id: int) -> Dict[str, Any]:
    """Получает полный контекст пользователя"""
    async with get_db() as session:
        user = await session.get(User, user_id)
        if not user:
            return {}
            
        # Получаем последние метрики
        latest_metrics = await session.execute(
            select(UserInteractionMetrics)
            .where(UserInteractionMetrics.user_id == user_id)
            .order_by(UserInteractionMetrics.date.desc())
            .limit(1)
        )
        metrics = latest_metrics.scalar_one_or_none()
        
        # Получаем последние эмоциональные состояния
        recent_states = await session.execute(
            select(DialogEmotionalState)
            .join(DialogEmotionalState.session)
            .where(DialogEmotionalState.session.has(user_id=user_id))
            .order_by(DialogEmotionalState.timestamp.desc())
            .limit(5)
        )
        emotional_states = recent_states.scalars().all()
        
        # Получаем активные задачи
        active_tasks = await session.execute(
            select(Task)
            .where(
                Task.user_id == user_id,
                Task.is_completed == False,
                Task.is_cancelled == False
            )
            .order_by(Task.due_date)
        )
        tasks = active_tasks.scalars().all()
        
        return {
            "user_preferences": user.interaction_preferences,
            "productivity_patterns": user.productivity_patterns,
            "stress_indicators": user.stress_indicators,
            "achievement_history": user.achievement_history,
            "current_challenges": user.current_challenges,
            "metrics": {
                "task_completion_rate": metrics.task_completion_rate if metrics else None,
                "preferred_hours": metrics.most_productive_hours if metrics else [],
                "interaction_style": metrics.preferred_interaction_style if metrics else None
            },
            "emotional_context": {
                "current_state": emotional_states[0].state if emotional_states else None,
                "recent_states": [state.state for state in emotional_states[1:]] if emotional_states else [],
                "stress_level": analyze_stress_level(emotional_states) if emotional_states else "normal"
            },
            "task_context": {
                "active_tasks": len(tasks),
                "overdue_tasks": sum(1 for task in tasks if task.is_overdue()),
                "upcoming_deadlines": [
                    {"title": task.title, "due_date": task.due_date}
                    for task in tasks if (task.due_date - datetime.now()).days <= 3
                ],
                "workload_level": calculate_workload_level(tasks)
            }
        }

def analyze_stress_level(emotional_states: List[DialogEmotionalState]) -> str:
    """Анализирует уровень стресса на основе истории эмоциональных состояний"""
    if not emotional_states:
        return "normal"
        
    stress_indicators = sum(
        1 for state in emotional_states 
        if state.state in [EmotionalState.STRESSED, EmotionalState.OVERWHELMED]
    )
    
    if stress_indicators >= 3:
        return "high"
    elif stress_indicators >= 1:
        return "moderate"
    return "normal"

def calculate_workload_level(tasks: List[Task]) -> str:
    """Оценивает уровень загрузки пользователя"""
    if not tasks:
        return "low"
        
    urgent_tasks = sum(1 for task in tasks if (task.due_date - datetime.now()).days <= 1)
    upcoming_tasks = sum(1 for task in tasks if 1 < (task.due_date - datetime.now()).days <= 7)
    
    if urgent_tasks >= 3 or (urgent_tasks >= 2 and upcoming_tasks >= 4):
        return "high"
    elif urgent_tasks >= 1 or upcoming_tasks >= 3:
        return "moderate"
    return "low"