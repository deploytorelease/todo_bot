from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select
from models import Task, User
from ai_module import generate_personalized_message
import logging
from database import get_db
from aiogram import Dispatcher
from ai_module import generate_personalized_message
from message_utils import send_personalized_message, get_user, get_task
from sqlalchemy import func
from ai_module import analyze_expenses
from models import FinancialRecord, RegularPayment


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler(bot):
    scheduler.start()
    logging.info("Scheduler started")
    scheduler.add_job(send_daily_reminders, 'cron', hour=9, minute=0, args=[bot])
    scheduler.add_job(send_upcoming_reminders, 'interval', minutes=5, args=[bot])
    scheduler.add_job(send_overdue_reminders, 'interval', minutes=30, args=[bot])
    scheduler.add_job(weekly_expense_analysis, 'cron', day_of_week='mon', hour=9, minute=0, args=[bot])
    scheduler.add_job(process_regular_payments, 'cron', day_of_week='mon', hour=9, minute=0, args=[bot])
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
    logger.info(f"Начало отправки напоминания для задачи {task_id} пользователю {user_id}")
    try:
        async with get_db() as session:
            task = await session.get(Task, task_id)
            user = await session.get(User, user_id)

            if task and not task.is_completed:
                logger.info(f"Задача найдена: {task.title}, статус: {'завершена' if task.is_completed else 'не завершена'}")
                message = await generate_personalized_message(user, 'task_reminder', task_title=task.title)
                logger.info(f"Сгенерировано сообщение: {message}")
                
                try:
                    await bot.send_message(chat_id=user.user_id, text=message)
                    logger.info(f"Напоминание отправлено для задачи: {task.title} пользователю: {user.user_id} в {datetime.now()}")
                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания пользователю {user.user_id}: {e}", exc_info=True)
            else:
                logger.warning(f"Задача {task_id} не найдена или уже завершена")
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}", exc_info=True)

async def weekly_expense_analysis(bot):
    logger.info("Начало еженедельного анализа финансов")
    async with get_db() as session:
        users = await session.execute(select(User))
        users = users.scalars().all()

        for user in users:
            if user.last_expense_analysis is None or (datetime.now() - user.last_expense_analysis).days >= 7:
                week_ago = datetime.now() - timedelta(days=7)
                financial_records = await session.execute(
                    select(FinancialRecord)
                    .where(FinancialRecord.user_id == user.user_id)
                    .where(FinancialRecord.date >= week_ago)
                )
                financial_records = financial_records.scalars().all()

                expense_data = [
                    {
                        "amount": record.amount,
                        "currency": record.currency,
                        "category": record.category,
                        "description": record.description,
                        "date": record.date.isoformat(),
                        "is_planned": record.is_planned,
                        "is_savings": record.is_savings
                    }
                    for record in financial_records if record.type == 'expense'
                ]

                income_data = [
                    {
                        "amount": record.amount,
                        "currency": record.currency,
                        "category": record.category,
                        "description": record.description,
                        "date": record.date.isoformat()
                    }
                    for record in financial_records if record.type == 'income'
                ]

                analysis = await analyze_expenses(expense_data, income_data)

                await bot.send_message(chat_id=user.user_id, text=analysis)
                user.last_expense_analysis = datetime.now()
                await session.commit()

    logger.info("Завершение еженедельного анализа финансов")

async def process_regular_payments(bot):
    logger.info("Начало обработки регулярных платежей")
    async with get_db() as session:
        today = datetime.now().date()
        payments = await session.execute(
            select(RegularPayment).where(RegularPayment.next_payment_date <= today)
        )
        payments = payments.scalars().all()

        for payment in payments:
            new_record = FinancialRecord(
                user_id=payment.user_id,
                amount=payment.amount,
                currency=payment.currency,
                category=payment.category,
                description=payment.description,
                type='expense',
                is_planned=True
            )
            session.add(new_record)

            # Обновляем дату следующего платежа
            if payment.frequency == 'monthly':
                payment.next_payment_date += timedelta(days=30)
            elif payment.frequency == 'quarterly':
                payment.next_payment_date += timedelta(days=91)
            elif payment.frequency == 'annually':
                payment.next_payment_date += timedelta(days=365)

            await bot.send_message(
                chat_id=payment.user_id,
                text=f"Автоматически внесен регулярный платеж: {payment.amount} {payment.currency} в категории {payment.category}."
            )

        await session.commit()
    logger.info("Завершение обработки регулярных платежей")


async def send_motivational_reminder(bot, user_id, task_id):
    try:
        task = await get_task(task_id)
        if task and not task.is_completed:
            await send_personalized_message(bot, user_id, 'motivation', task_title=task.title)
            logger.info(f"Motivational reminder sent for task: {task.title} to user: {user_id}")

            # Сохраняем состояние ожидания ответа
            dp = Dispatcher.get_current()
            state = dp.current_state(chat=user_id, user=user_id)
            await state.set_state("waiting_for_task_completion")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке мотивирующего напоминания пользователю {user_id}: {e}", exc_info=True)

async def send_upcoming_reminders(bot):
    now = datetime.now()
    upcoming = now + timedelta(minutes=15)
    logging.info(f"Checking for upcoming tasks between {now} and {upcoming}")
    try:
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
    except Exception as e:
        logging.error(f"Ошибка при проверке предстоящих задач: {e}")

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