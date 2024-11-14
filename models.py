from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text, Interval, Enum
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime, timedelta
import json
import enum


Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True)
    tone = Column(String, default='neutral')
    role = Column(String, default='assistant')
    learning_topic = Column(String, nullable=True)
    learning_progress = Column(Integer, default=0)
    last_expense_analysis = Column(DateTime, nullable=True)
    preferred_reminder_time = Column(String, nullable=True)
    notification_settings = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    interaction_preferences = Column(JSONB, default={})  # Предпочтения в общении
    productivity_patterns = Column(JSONB, default={})    # Паттерны продуктивности
    stress_indicators = Column(JSONB, default={})        # Индикаторы стресса
    achievement_history = Column(JSONB, default={})      # История достижений
    current_challenges = Column(JSONB, default=[])       # Текущие сложности
    support_history = Column(JSONB, default={})          # История поддержки
    
        # Связи
    dialog_sessions = relationship("DialogSession", back_populates="user")
    interaction_metrics = relationship("UserInteractionMetrics", back_populates="user")
    emotional_states = relationship("UserEmotionalState", back_populates="user")
    tasks = relationship("Task", back_populates="owner")
    financial_records = relationship("FinancialRecord", back_populates="owner")
    regular_payments = relationship("RegularPayment", back_populates="owner")
    goals = relationship("Goal", back_populates="owner")
    reminders = relationship("ReminderEffectiveness", back_populates="user")
    completed_tasks = relationship("CompletedTask", back_populates="owner")

    def get_notification_settings(self):
        if not self.notification_settings:
            return {
                "daily_summary": True,
                "task_reminders": True,
                "financial_reports": True,
                "urgent_only": False,
                "quiet_hours": {"start": "23:00", "end": "07:00"}
            }
        return json.loads(self.notification_settings)

    def get_preferred_reminder_time(self):
        if not self.preferred_reminder_time:
            return {
                "morning": "09:00",
                "afternoon": "14:00",
                "evening": "19:00"
            }
        return json.loads(self.preferred_reminder_time)
    
class DialogSession(Base):
    """Сессия диалога с пользователем"""
    __tablename__ = 'dialog_sessions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    start_time = Column(DateTime, default=datetime.now)
    end_time = Column(DateTime, nullable=True)
    topic = Column(String)
    context = Column(JSONB, default={})
    messages = Column(JSONB, default=[])
    identified_issues = Column(JSONB, default=[])
    proposed_solutions = Column(JSONB, default=[])
    next_steps = Column(JSONB, default=[])
    effectiveness_rating = Column(Integer, nullable=True)  # Оценка пользователем
    
    user = relationship("User", back_populates="dialog_sessions")
    emotional_states = relationship("DialogEmotionalState", back_populates="session")

class UserInteractionMetrics(Base):
    """Метрики взаимодействия с пользователем"""
    __tablename__ = 'user_interaction_metrics'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    date = Column(DateTime, default=datetime.now)
    
    # Метрики задач
    task_completion_rate = Column(Float, default=0.0)
    average_task_delay = Column(Integer, default=0)  # в часах
    task_complexity_preference = Column(JSONB, default={})
    
    # Метрики времени
    most_productive_hours = Column(JSONB, default=[])
    response_times = Column(JSONB, default={})
    break_patterns = Column(JSONB, default={})
    
    # Метрики взаимодействия
    preferred_interaction_style = Column(String, nullable=True)
    communication_patterns = Column(JSONB, default={})
    support_effectiveness = Column(JSONB, default={})
    
    user = relationship("User", back_populates="interaction_metrics")

class EmotionalState(enum.Enum):
    MOTIVATED = "motivated"
    STRESSED = "stressed"
    OVERWHELMED = "overwhelmed"
    FOCUSED = "focused"
    PROCRASTINATING = "procrastinating"
    NEUTRAL = "neutral"

class DialogEmotionalState(Base):
    """Эмоциональное состояние в рамках диалога"""
    __tablename__ = 'dialog_emotional_states'
    
    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('dialog_sessions.id'))
    timestamp = Column(DateTime, default=datetime.now)
    state = Column(Enum(EmotionalState))
    confidence = Column(Float, default=0.0)
    triggers = Column(JSONB, default=[])
    
    session = relationship("DialogSession", back_populates="emotional_states")

class UserEmotionalState(Base):
    __tablename__ = 'user_emotional_states'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    timestamp = Column(DateTime, default=datetime.now)
    state = Column(Enum(EmotionalState))
    confidence = Column(Float, default=0.0)
    context = Column(JSONB, default={})
    
    user = relationship("User", back_populates="emotional_states")

class TaskCategory(Base):
    __tablename__ = 'task_categories'
    
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(Integer, default=0)
    color = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    
    tasks = relationship("Task", back_populates="category_rel")

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    category_id = Column(Integer, ForeignKey('task_categories.id'), nullable=True)
    title = Column(String)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime)
    start_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    priority = Column(String)
    last_reminder = Column(DateTime, nullable=True)
    reminder_count = Column(Integer, default=0)
    upcoming_reminder_sent = Column(Boolean, default=False)
    last_overdue_reminder = Column(DateTime, nullable=True)
    is_cancelled = Column(Boolean, default=False)
    cancellation_date = Column(DateTime, nullable=True)
    cancellation_reason = Column(String, nullable=True)
    scheduler_job_id = Column(String, nullable=True)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=True)
    order = Column(Integer, nullable=True)
    dependencies = Column(String, nullable=True)
    can_parallel = Column(Boolean, default=False)
    progress_metrics = Column(String, nullable=True)
    resources = Column(String, nullable=True)
    deliverables = Column(String, nullable=True)
    
    owner = relationship("User", back_populates="tasks")
    category_rel = relationship("TaskCategory", back_populates="tasks")
    goal = relationship("Goal", back_populates="tasks")

    def is_overdue(self):
        return not self.is_completed and self.due_date < datetime.now()

    def get_dependencies(self):
        if not self.dependencies:
            return []
        return json.loads(self.dependencies)

    def get_progress_metrics(self):
        if not self.progress_metrics:
            return {}
        return json.loads(self.progress_metrics)

class ReminderEffectiveness(Base):
    __tablename__ = 'reminder_effectiveness'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    completion_rate = Column(Float)
    response_time = Column(Interval)
    optimal_intervals = Column(String)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    
    user = relationship("User", back_populates="reminders")

    def to_dict(self):
        return {
            'completion_rate': self.completion_rate,
            'response_time': self.response_time.total_seconds() if self.response_time else None,
            'optimal_intervals': json.loads(self.optimal_intervals) if self.optimal_intervals else {}
        }

class FinancialRecord(Base):
    __tablename__ = 'financial_records'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    amount = Column(Float)
    currency = Column(String)
    category = Column(String)
    description = Column(Text, nullable=True)
    date = Column(DateTime, default=datetime.now)
    type = Column(String)
    is_planned = Column(Boolean, default=False)
    is_savings = Column(Boolean, default=False)
    regular_payment_id = Column(Integer, ForeignKey('regular_payments.id'), nullable=True)
    tags = Column(String, nullable=True)

    owner = relationship("User", back_populates="financial_records")
    regular_payment = relationship("RegularPayment", back_populates="records")

    def get_tags(self):
        if not self.tags:
            return []
        return json.loads(self.tags)

class RegularPayment(Base):
    __tablename__ = 'regular_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    amount = Column(Float)
    currency = Column(String)
    category = Column(String)
    description = Column(Text, nullable=True)
    frequency = Column(String)
    next_payment_date = Column(DateTime)
    is_active = Column(Boolean, default=True)
    start_date = Column(DateTime, default=datetime.now)
    end_date = Column(DateTime, nullable=True)
    last_processed = Column(DateTime, nullable=True)
    failure_count = Column(Integer, default=0)
    notification_days_before = Column(Integer, default=3)

    owner = relationship("User", back_populates="regular_payments")
    records = relationship("FinancialRecord", back_populates="regular_payment")

    def calculate_next_payment_date(self):
        if not self.next_payment_date:
            return None
            
        if self.frequency == 'monthly':
            return self.next_payment_date + timedelta(days=30)
        elif self.frequency == 'quarterly':
            return self.next_payment_date + timedelta(days=91)
        elif self.frequency == 'annually':
            return self.next_payment_date + timedelta(days=365)
        
        return None

class Goal(Base):
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    title = Column(String)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)
    user_experience = Column(String, nullable=True)
    available_time = Column(String, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    is_completed = Column(Boolean, default=False)
    status = Column(String, default='active')
    priority = Column(Integer, default=1)
    
    owner = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan")
    milestones = relationship("Milestone", back_populates="goal", cascade="all, delete-orphan")
    steps = relationship("GoalStep", back_populates="goal")

class GoalStep(Base):
    __tablename__ = 'goal_steps'

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey('goals.id'))
    description = Column(String)
    is_completed = Column(Boolean, default=False)
    completion_date = Column(DateTime, nullable=True)
    order = Column(Integer)
    expected_duration = Column(Interval, nullable=True)
    actual_duration = Column(Interval, nullable=True)
    dependencies = Column(String, nullable=True)

    goal = relationship("Goal", back_populates="steps")

class Milestone(Base):
    __tablename__ = 'milestones'
    
    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey('goals.id'))
    title = Column(String)
    description = Column(Text, nullable=True)
    expected_date = Column(DateTime)
    actual_date = Column(DateTime, nullable=True)
    success_criteria = Column(String)
    completed = Column(Boolean, default=False)
    completion_notes = Column(Text, nullable=True)
    
    goal = relationship("Goal", back_populates="milestones")

class CompletedTask(Base):
    __tablename__ = 'completed_tasks'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    title = Column(String)
    description = Column(Text, nullable=True)
    completion_date = Column(DateTime, default=datetime.now)
    original_due_date = Column(DateTime)
    category = Column(String)
    time_spent = Column(Interval, nullable=True)
    difficulty_rating = Column(Integer, nullable=True)
    completion_notes = Column(Text, nullable=True)
    
    owner = relationship("User", back_populates="completed_tasks")