from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select
from models import Task, User
from ai_module import generate_personalized_message
import logging
from database import get_db
from aiogram import Dispatcher
from ai_module import generate_personalized_message

scheduler = AsyncIOScheduler()

def start_scheduler(bot):
    scheduler.start()
    logging.info("Scheduler started")
    scheduler.add_job(send_daily_reminders, 'cron', hour=9, minute=0, args=[bot])
    scheduler.add_job(send_upcoming_reminders, 'interval', minutes=5, args=[bot])
    scheduler.add_job(send_overdue_reminders, 'interval', minutes=30, args=[bot])
    logging.info("All jobs added to scheduler")

async def send_daily_reminders(bot):
    now = datetime.now()
    today = now.date()
    async with get_db() as session:
        result = await session.execute(
            select(Task, User).join(User).where(
                Task.due_date.between(today, today + timedelta(days=1)),
                Task.is_completed == False
            )
        )
        tasks = result.all()

        for task, user in tasks:
            message = await generate_personalized_message(user, 'daily_reminder', task_title=task.title)
            try:
                await bot.send_message(chat_id=user.user_id, text=message)
            except Exception as e:
                logging.error(f"Ошибка при отправке ежедневного напоминания пользователю {user.user_id}: {e}")


async def send_task_reminder(bot, user_id, task_id):
    async with get_db() as session:
        task = await session.get(Task, task_id)
        user = await session.get(User, user_id)

        if task and not task.is_completed:
            # Отправляем простое напоминание
            message = f"🌟 Пора выполнить задачу: \"{task.title}\"."
            try:
                await bot.send_message(chat_id=user.user_id, text=message)
                logging.info(f"Reminder sent for task: {task.title} to user: {user.user_id} at {datetime.now()}")
            except Exception as e:
                logging.error(f"Ошибка при отправке напоминания пользователю {user.user_id}: {e}")

async def check_user_response(bot, user_id, task_id):
    dp = Dispatcher.get_current()
    state = dp.current_state(chat=user_id, user=user_id)
    user_state = await state.get_state()
    data = await state.get_data()

    if user_state == "waiting_for_task_completion" and data.get('task_id') == task_id:
        reminder_stage = data.get('reminder_stage', 1)
        if reminder_stage == 1:
            # Пользователь не ответил или ответил отрицательно
            # Планируем мотивирующее напоминание через 30 минут
            await state.update_data(reminder_stage=2)
            scheduler.add_job(
                send_motivational_reminder,
                'date',
                run_date=datetime.now() + timedelta(minutes=30),
                args=[bot, user_id, task_id]
            )

async def send_motivational_reminder(bot, user_id, task_id):
    async with get_db() as session:
        task = await session.get(Task, task_id)
        user = await session.get(User, user_id)

        if task and not task.is_completed:
            # Генерируем мотивирующее сообщение
            message = await generate_personalized_message(user, 'motivation', task_title=task.title)
            try:
                await bot.send_message(chat_id=user.user_id, text=message)
                logging.info(f"Motivational reminder sent for task: {task.title} to user: {user.user_id}")

                # Сохраняем состояние ожидания ответа
                dp = Dispatcher.get_current()
                state = dp.current_state(chat=user.user_id, user=user.user_id)
                await state.set_state("waiting_for_task_completion")
                
                # Планируем повторную проверку ответа через 5 минут
                scheduler.add_job(
                    check_user_response, 
                    'date', 
                    run_date=datetime.now() + timedelta(minutes=5), 
                    args=[bot, user.user_id, task.id]
                )
            except Exception as e:
                logging.error(f"Ошибка при отправке мотивирующего напоминания пользователю {user.user_id}: {e}")
        else:
            # Если задача уже выполнена, очищаем состояние
            state = dp.current_state(chat=user_id, user=user_id)
            await state.finish()

async def send_upcoming_reminders(bot):
    now = datetime.now()
    upcoming = now + timedelta(minutes=15)
    logging.info(f"Checking for upcoming tasks between {now} and {upcoming}")
    async with get_db() as session:
        result = await session.execute(
            select(Task, User).join(User).where(
                Task.due_date.between(now, upcoming),
                Task.is_completed == False,
                Task.upcoming_reminder_sent == False
            )
        )
        tasks = result.all()
        logging.info(f"Found {len(tasks)} tasks to remind about")
        for task, user in tasks:
            logging.info(f"Sending reminder for task: {task.title} to user: {user.user_id}")
            message = await generate_personalized_message(user, 'upcoming_reminder', task_title=task.title)
            try:
                await bot.send_message(chat_id=user.user_id, text=message)
                task.upcoming_reminder_sent = True
                await session.commit()
            except Exception as e:
                logging.error(f"Ошибка при отправке напоминания о скором начале задачи пользователю {user.user_id}: {e}")

async def send_overdue_reminders(bot):
    now = datetime.now()
    async with get_db() as session:
        result = await session.execute(
            select(Task, User).join(User).where(
                Task.due_date <= now,
                Task.is_completed == False,
                Task.last_overdue_reminder == None
            )
        )
        tasks = result.all()

        for task, user in tasks:
            message = await generate_personalized_message(user, 'overdue_reminder', task_title=task.title)
            try:
                await bot.send_message(chat_id=user.user_id, text=message)
                task.last_overdue_reminder = now
                await session.commit()
            except Exception as e:
                logging.error(f"Ошибка при отправке напоминания о просроченной задаче пользователю {user.user_id}: {e}")