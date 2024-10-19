# models.py

from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'

    user_id = Column(Integer, primary_key=True, index=True)
    tone = Column(String, default='neutral')
    role = Column(String, default='assistant')
    learning_topic = Column(String, nullable=True)
    learning_progress = Column(Integer, default=0)
    tasks = relationship("Task", back_populates="owner")
    financial_records = relationship("FinancialRecord", back_populates="owner")
    regular_payments = relationship("RegularPayment", back_populates="owner")
    goals = relationship("Goal", back_populates="owner")
    last_expense_analysis = Column(DateTime, nullable=True)

class Task(Base):
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    title = Column(String)
    description = Column(Text, nullable=True)
    due_date = Column(DateTime)
    is_completed = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    priority = Column(String)
    category = Column(String)
    last_reminder = Column(DateTime, nullable=True)
    upcoming_reminder_sent = Column(Boolean, default=False)
    last_overdue_reminder = Column(DateTime, nullable=True)
    owner = relationship("User", back_populates="tasks")
    scheduler_job_id = Column(String, nullable=True)

class FinancialRecord(Base):
    __tablename__ = 'financial_records'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    amount = Column(Float)
    currency = Column(String)  # Новое поле
    category = Column(String)
    description = Column(Text, nullable=True)
    date = Column(DateTime, default=datetime.utcnow)
    type = Column(String)  # 'income' или 'expense'
    is_planned = Column(Boolean, default=False)  # Для запланированных трат
    is_savings = Column(Boolean, default=False)  # Для отложенных денег

    owner = relationship("User", back_populates="financial_records")

class RegularPayment(Base):
    __tablename__ = 'regular_payments'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    amount = Column(Float)
    currency = Column(String)
    category = Column(String)
    description = Column(Text, nullable=True)
    frequency = Column(String)  # 'monthly', 'quarterly', 'annually', etc.
    next_payment_date = Column(DateTime)

    owner = relationship("User", back_populates="regular_payments")

class Goal(Base):
    __tablename__ = 'goals'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    title = Column(String)
    description = Column(Text, nullable=True)
    deadline = Column(DateTime)
    progress = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    owner = relationship("User", back_populates="goals")
    steps = relationship("GoalStep", back_populates="goal")

class GoalStep(Base):
    __tablename__ = 'goal_steps'

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey('goals.id'))
    description = Column(String)
    is_completed = Column(Boolean, default=False)
    order = Column(Integer)

    goal = relationship("Goal", back_populates="steps")

class CompletedTask(Base):
    __tablename__ = 'completed_tasks'

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.user_id'))
    title = Column(String)
    description = Column(Text, nullable=True)
    completion_date = Column(DateTime, default=datetime.utcnow)
    original_due_date = Column(DateTime)
    category = Column(String)

    owner = relationship("User")