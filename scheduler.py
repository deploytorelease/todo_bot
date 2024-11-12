from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta
from sqlalchemy import select, or_, func
from models import Task, User, FinancialRecord, RegularPayment, ReminderEffectiveness, TaskCategory
from ai_module import generate_personalized_message, analyze_expenses
from database import get_db
from message_utils import send_personalized_message
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
import logging
import json


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()

def start_scheduler(bot):
    """Инициализация и запуск планировщика задач"""
    scheduler.start()
    logger.info("Scheduler started")
    
    # Ежедневные проверки
    scheduler.add_job(send_daily_summary, 'cron', hour=9, minute=0, args=[bot])
    
    # Регулярные проверки задач
    scheduler.add_job(check_tasks, 'interval', minutes=15, args=[bot])
    scheduler.add_job(send_overdue_reminders, 'interval', minutes=30, args=[bot])
    
    # Еженедельные финансовые проверки
    scheduler.add_job(weekly_expense_analysis, 'cron', 
                     day_of_week='mon', hour=9, minute=0, args=[bot])
    scheduler.add_job(process_regular_payments, 'cron', 
                     day_of_week='mon', hour=9, minute=0, args=[bot])
    
    # Анализ эффективности напоминаний
    scheduler.add_job(analyze_reminder_effectiveness, 'cron', 
                     hour=3, minute=0, args=[bot])
    
    logger.info("All jobs added to scheduler")

async def send_overdue_reminders(bot):
    """Проверяет и отправляет напоминания о просроченных задачах"""
    logger.info("Проверка просроченных задач")
    
    try:
        async with get_db() as session:
            now = datetime.now()
            # Получаем просроченные задачи, о которых давно не напоминали
            result = await session.execute(
                select(Task, User).join(User).where(
                    Task.due_date <= now,
                    Task.is_completed == False,
                    or_(
                        Task.last_overdue_reminder == None,
                        Task.last_overdue_reminder <= now - timedelta(hours=4)  # Напоминаем каждые 4 часа
                    )
                )
            )
            tasks = result.all()

            for task, user in tasks:
                try:
                    # Считаем, сколько времени прошло с дедлайна
                    overdue_time = now - task.due_date
                    overdue_hours = overdue_time.total_seconds() / 3600

                    # Создаем текст напоминания в зависимости от просрочки
                    if overdue_hours < 24:
                        severity = "⚠️"
                        time_text = f"{int(overdue_hours)} час(ов)"
                    else:
                        severity = "🚨"
                        days = int(overdue_hours / 24)
                        time_text = f"{days} дней"

                    # Формируем клавиатуру с действиями
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="✅ Выполнено", 
                                            callback_data=f"complete_{task.id}")],
                        [InlineKeyboardButton(text="📅 Перенести срок", 
                                            callback_data=f"reschedule_{task.id}")],
                        [InlineKeyboardButton(text="❌ Отменить задачу", 
                                            callback_data=f"cancel_{task.id}")]
                    ])

                    # Генерируем персонализированное сообщение
                    message = await generate_personalized_message(
                        user,
                        'overdue_reminder',
                        task_title=task.title,
                        overdue_time=time_text
                    )

                    await bot.send_message(
                        chat_id=user.user_id,
                        text=f"{severity} {message}",
                        reply_markup=keyboard
                    )

                    # Обновляем время последнего напоминания
                    task.last_overdue_reminder = now
                    task.reminder_count = (task.reminder_count or 0) + 1
                    await session.commit()

                    logger.info(f"Отправлено напоминание о просроченной задаче {task.id}")

                except Exception as e:
                    logger.error(f"Ошибка при отправке напоминания о задаче {task.id}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Ошибка при проверке просроченных задач: {e}")

async def send_daily_summary(bot):
    """Отправляет ежедневную сводку пользователям"""
    logger.info("Отправка ежедневной сводки")
    try:
        async with get_db() as session:
            users = await session.execute(select(User))
            for user in users.scalars():
                try:
                    today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
                    today_end = today_start + timedelta(days=1)
                    
                    # Получаем задачи по категориям
                    tasks_query = await session.execute(
                        select(Task, TaskCategory)
                        .outerjoin(TaskCategory)
                        .where(
                            Task.user_id == user.user_id,
                            Task.is_completed == False
                        )
                        .order_by(TaskCategory.priority.desc(), Task.due_date)
                    )
                    all_tasks = tasks_query.all()
                    
                    # Разделяем задачи по типам
                    today_tasks = []
                    overdue_tasks = []
                    upcoming_tasks = []
                    for task, category in all_tasks:
                        if task.due_date < today_start:
                            overdue_tasks.append((task, category))
                        elif task.due_date <= today_end:
                            today_tasks.append((task, category))
                        elif task.due_date <= today_end + timedelta(days=2):
                            upcoming_tasks.append((task, category))
                    
                    if any([today_tasks, overdue_tasks, upcoming_tasks]):
                        message = "🌅 Доброе утро! Вот ваша сводка задач:\n\n"
                        
                        if overdue_tasks:
                            message += "🚨 Просроченные задачи:\n"
                            for task, category in overdue_tasks:
                                days_overdue = (datetime.now() - task.due_date).days
                                category_name = category.name if category else "Без категории"
                                message += (f"• [{category_name}] {task.title}"
                                          f" (просрочено на {days_overdue} дн.)\n")
                            message += "\n"
                        
                        if today_tasks:
                            message += "📋 Задачи на сегодня:\n"
                            for task, category in today_tasks:
                                category_name = category.name if category else "Без категории"
                                message += (f"• [{category_name}] {task.title}"
                                          f" (к {task.due_date.strftime('%H:%M')})\n")
                            message += "\n"
                        
                        if upcoming_tasks:
                            message += "📅 Ближайшие задачи:\n"
                            for task, category in upcoming_tasks:
                                category_name = category.name if category else "Без категории"
                                message += (f"• [{category_name}] {task.title}"
                                          f" ({task.due_date.strftime('%d.%m %H:%M')})\n")
                        
                        # Добавляем статистику
                        completed_today = await session.execute(
                            select(func.count(Task.id))
                            .where(
                                Task.user_id == user.user_id,
                                Task.completion_date >= today_start,
                                Task.is_completed == True
                            )
                        )
                        completed_count = completed_today.scalar_one()
                        
                        if completed_count > 0:
                            message += f"\n✨ Сегодня вы уже выполнили {completed_count} задач!"
                        
                        await bot.send_message(chat_id=user.user_id, text=message)
                        
                except Exception as e:
                    logger.error(f"Ошибка при отправке сводки пользователю {user.user_id}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Ошибка при отправке ежедневной сводки: {e}")

async def analyze_reminder_effectiveness(bot):
    """Анализирует эффективность напоминаний для каждого пользователя"""
    try:
        async with get_db() as session:
            users = await session.execute(select(User))
            for user in users.scalars():
                try:
                    # Анализируем последние 20 задач пользователя
                    tasks = await session.execute(
                        select(Task)
                        .where(Task.user_id == user.user_id)
                        .order_by(Task.created_at.desc())
                        .limit(20)
                    )
                    tasks = tasks.scalars().all()
                    if tasks:
                        total_tasks = len(tasks)
                        completed_tasks = sum(1 for task in tasks if task.is_completed)
                        completed_on_time = sum(1 for task in tasks 
                                              if task.is_completed and task.completion_date <= task.due_date)
                        
                        # Рассчитываем метрики
                        completion_rate = completed_tasks / total_tasks
                        on_time_rate = completed_on_time / completed_tasks if completed_tasks > 0 else 0
                        
                        # Среднее время выполнения после напоминания
                        completion_times = []
                        for task in tasks:
                            if task.is_completed and task.last_reminder:
                                time_diff = task.completion_date - task.last_reminder
                                completion_times.append(time_diff.total_seconds())
                        
                        avg_completion_time = (sum(completion_times) / len(completion_times) 
                                             if completion_times else 0)
                        
                        # Сохраняем или обновляем метрики
                        effectiveness = await session.execute(
                            select(ReminderEffectiveness)
                            .where(ReminderEffectiveness.user_id == user.user_id)
                        )
                        effectiveness = effectiveness.scalar_one_or_none()
                        
                        if effectiveness:
                            effectiveness.completion_rate = completion_rate
                            effectiveness.on_time_rate = on_time_rate
                            effectiveness.average_completion_time = timedelta(seconds=avg_completion_time)
                            effectiveness.updated_at = datetime.now()
                        else:
                            effectiveness = ReminderEffectiveness(
                                user_id=user.user_id,
                                completion_rate=completion_rate,
                                on_time_rate=on_time_rate,
                                average_completion_time=timedelta(seconds=avg_completion_time)
                            )
                            session.add(effectiveness)
                        
                        await session.commit()
                        
                except Exception as e:
                    logger.error(f"Ошибка при анализе эффективности для пользователя {user.user_id}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Ошибка при анализе эффективности напоминаний: {e}")

async def calculate_next_reminder_interval(user_id: int, task: Task) -> timedelta:
    """Рассчитывает интервал до следующего напоминания на основе эффективности"""
    try:
        async with get_db() as session:
            effectiveness = await session.execute(
                select(ReminderEffectiveness)
                .where(ReminderEffectiveness.user_id == user_id)
            )
            effectiveness = effectiveness.scalar_one_or_none()
            
            if not effectiveness:
                return timedelta(minutes=30)  # Значение по умолчанию
            # Базовый интервал зависит от эффективности
            base_interval = timedelta(minutes=30)
            if effectiveness.completion_rate < 0.3:
                base_interval = timedelta(minutes=15)  # Чаще для менее ответственных
            elif effectiveness.completion_rate > 0.7:
                base_interval = timedelta(hours=1)  # Реже для ответственных
            
            # Учитываем срочность задачи
            time_until_due = task.due_date - datetime.now()
            if time_until_due < timedelta(hours=1):
                base_interval = timedelta(minutes=10)  # Очень частые напоминания при близком дедлайне
            elif time_until_due < timedelta(hours=3):
                base_interval = min(base_interval, timedelta(minutes=20))
            
            # Учитываем историю напоминаний
            if task.reminder_count and task.reminder_count > 3:
                base_interval *= 1.5  # Увеличиваем интервал, если уже много напоминали
            
            return base_interval
            
    except Exception as e:
        logger.error(f"Ошибка при расчете интервала напоминаний: {e}")
        return timedelta(minutes=30)

async def send_task_reminder(bot, user_id: int, task_id: int, reminder_type: str = 'regular'):
    """
    Отправляет напоминание о задаче с учетом контекста, истории и эффективности
    
    Args:
        bot: Объект бота
        user_id: ID пользователя
        task_id: ID задачи
        reminder_type: Тип напоминания ('regular', 'urgent', 'overdue')
    """
    logger.info(f"Отправка напоминания type={reminder_type} для задачи {task_id} пользователю {user_id}")
    
    try:
        async with get_db() as session:
            task = await session.get(Task, task_id)
            user = await session.get(User, user_id)
            
            if not task or task.is_completed:
                return
            
            # Проверяем эффективность предыдущих напоминаний
            effectiveness = await session.execute(
                select(ReminderEffectiveness)
                .where(ReminderEffectiveness.user_id == user_id)
                .order_by(ReminderEffectiveness.updated_at.desc())
                .limit(1)
            )
            effectiveness = effectiveness.scalar_one_or_none()
            # Настраиваем сообщение на основе эффективности
            if effectiveness:
                if effectiveness.completion_rate < 0.3:  # Низкая эффективность
                    reminder_type = 'urgent'  # Усиливаем важность
                elif effectiveness.average_completion_time.total_seconds() > 86400:  # Больше суток
                    reminder_type = 'motivational'  # Добавляем мотивацию
            
            # Создаем клавиатуру с действиями
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ Выполнено", 
                                    callback_data=f"complete_{task_id}")],
                [InlineKeyboardButton(text="⏰ Напомнить через час", 
                                    callback_data=f"remind_1h_{task_id}")],
                [InlineKeyboardButton(text="📅 Перенести на завтра", 
                                    callback_data=f"postpone_1d_{task_id}")]
            ])
            
            if reminder_type == 'overdue':
                keyboard.inline_keyboard.append([
                    InlineKeyboardButton(
                        text="❌ Отменить задачу",
                        callback_data=f"cancel_{task_id}"
                    )
                ])
            
            # Генерируем персонализированное сообщение
            message_data = {
                'task_title': task.title,
                'due_date': task.due_date.strftime("%d.%m.%Y %H:%M"),
                'overdue_time': str(datetime.now() - task.due_date) if reminder_type == 'overdue' else None,
                'previous_reminders': task.reminder_count or 0,
                'effectiveness': effectiveness.to_dict() if effectiveness else None
            }
            
            message = await generate_personalized_message(
                user,
                f'task_reminder_{reminder_type}',
                **message_data
            )
            
            # Добавляем эмодзи в зависимости от типа
            format_tags = {
                'regular': '📝',
                'urgent': '⚠️',
                'overdue': '🚨',
                'motivational': '💪'
            }
            formatted_message = f"{format_tags[reminder_type]} {message}"
            
            # Отправляем сообщение
            await bot.send_message(
                chat_id=user_id,
                text=formatted_message,
                reply_markup=keyboard
            )
            
            # Обновляем информацию о напоминании
            task.last_reminder = datetime.now()
            task.reminder_count = (task.reminder_count or 0) + 1
            
            # Планируем следующее напоминание с адаптивным интервалом
            next_interval = await calculate_next_reminder_interval(user_id, task)
            next_reminder_time = datetime.now() + next_interval
            
            scheduler.add_job(
                send_task_reminder,
                'date',
                run_date=next_reminder_time,
                args=[bot, user_id, task_id, 'regular']
            )
            await session.commit()
            logger.info(f"Напоминание успешно отправлено для задачи {task_id}")
            
    except Exception as e:
        logger.error(f"Ошибка при отправке напоминания: {e}", exc_info=True)

async def check_tasks(bot):
    """Проверяет предстоящие задачи и отправляет уведомления"""
    logger.info("Проверка предстоящих задач")
    try:
        async with get_db() as session:
            now = datetime.now()
            upcoming_window = now + timedelta(hours=2)
            
            tasks = await session.execute(
                select(Task, User).join(User).where(
                    Task.due_date.between(now, upcoming_window),
                    Task.is_completed == False,
                    or_(
                        Task.last_reminder == None,
                        Task.last_reminder <= now - timedelta(minutes=30)
                    )
                )
            )
            tasks = tasks.all()
            
            for task, user in tasks:
                try:
                    # Проверяем загруженность периода
                    time_window_start = task.due_date - timedelta(hours=1)
                    time_window_end = task.due_date + timedelta(hours=1)
                    
                    tasks_in_period = await session.execute(
                        select(func.count(Task.id)).where(
                            Task.user_id == user.user_id,
                            Task.due_date.between(time_window_start, time_window_end),
                            Task.is_completed == False
                        )
                    )
                    tasks_count = tasks_in_period.scalar_one()
                    
                    # Определяем тип напоминания
                    if task.due_date <= now:
                        reminder_type = 'overdue'
                    elif task.due_date <= now + timedelta(minutes=30):
                        reminder_type = 'urgent'
                    else:
                        reminder_type = 'regular'
                    
                    # Если много задач в один период, отправляем предупреждение
                    if tasks_count > 1:
                        await send_workload_warning(bot, user, task.due_date, tasks_count)
                    
                    await send_task_reminder(bot, user.user_id, task.id, reminder_type)
                    
                except Exception as e:
                    logger.error(f"Ошибка при обработке задачи {task.id}: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"Ошибка при проверке предстоящих задач: {e}")

async def send_workload_warning(bot, user, time_period, tasks_count):
    """Отправляет предупреждение о большом количестве задач в один период"""
    try:
        message = await generate_personalized_message(
            user,
            'multiple_tasks_warning',
            tasks_count=tasks_count,
            time_period=time_period.strftime("%H:%M")
        )
        
        await bot.send_message(
            chat_id=user.user_id,
            text=f"⚠️ {message}",
            parse_mode='HTML'
        )
        
    except Exception as e:
        logger.error(f"Ошибка при отправке предупреждения о нагрузке: {e}")

async def weekly_expense_analysis(bot):
    """Еженедельный анализ финансов пользователей"""
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

                # Подготавливаем данные для анализа
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
    """Обработка регулярных платежей"""
    logger.info("Начало обработки регулярных платежей")
    async with get_db() as session:
        today = datetime.now().date()
        payments = await session.execute(
            select(RegularPayment).where(RegularPayment.next_payment_date <= today)
        )
        payments = payments.scalars().all()

        for payment in payments:
            try:
                # Создаем запись о финансовой операции
                new_record = FinancialRecord(
                    user_id=payment.user_id,
                    amount=payment.amount,
                    currency=payment.currency,
                    category=payment.category,
                    description=payment.description,
                    type='expense',
                    is_planned=True,
                    date=datetime.now()
                )
                session.add(new_record)

                # Обновляем дату следующего платежа
                if payment.frequency == 'monthly':
                    payment.next_payment_date += timedelta(days=30)
                elif payment.frequency == 'quarterly':
                    payment.next_payment_date += timedelta(days=91)
                elif payment.frequency == 'annually':
                    payment.next_payment_date += timedelta(days=365)

                # Отправляем уведомление пользователю
                message = await generate_personalized_message(
                    user_id=payment.user_id,
                    message_type='regular_payment',
                    amount=payment.amount,
                    currency=payment.currency,
                    category=payment.category
                )
                
                await bot.send_message(
                    chat_id=payment.user_id,
                    text=message
                )

            except Exception as e:
                logger.error(f"Ошибка при обработке регулярного платежа {payment.id}: {e}")
                continue

        await session.commit()
    logger.info("Завершение обработки регулярных платежей")