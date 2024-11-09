# handlers.py

from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, FSInputFile
from database import get_db
from models import User, Task, CompletedTask, FinancialRecord, Goal, GoalStep
from ai_module import parse_message, generate_personalized_message, generate_goal_steps
from datetime import datetime, timedelta
from sqlalchemy import select, func
import logging
import matplotlib.pyplot as plt
import io
from scheduler import send_task_reminder, scheduler
from message_utils import send_personalized_message, get_user, get_task
from models import RegularPayment, Milestone
import json




logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Состояния FSM
class TaskStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_due_date = State()

class EditTaskStates(StatesGroup):
    waiting_for_task_id = State()
    waiting_for_new_title = State()
    waiting_for_new_due_date = State()

class ToneStates(StatesGroup):
    waiting_for_tone = State()

class LearningStates(StatesGroup):
    waiting_for_topic = State()

class GoalCreationStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_experience = State()
    waiting_for_available_time = State()
    
async def start_goal_creation(message: types.Message, state: FSMContext):
    await state.set_state(GoalCreationStates.waiting_for_title)
    await message.answer("Какую цель вы хотите достичь?")

async def process_goal_title(message: types.Message, state: FSMContext):
    await state.update_data(goal_title=message.text)
    await state.set_state(GoalCreationStates.waiting_for_experience)
    await message.answer(
        "Какой у вас опыт в этой области?\n"
        "1. Новичок\n"
        "2. Есть базовые знания\n"
        "3. Средний уровень\n"
        "4. Продвинутый"
    )

async def process_experience(message: types.Message, state: FSMContext):
    await state.update_data(experience=message.text)
    await state.set_state(GoalCreationStates.waiting_for_available_time)
    await message.answer(
        "Сколько времени в неделю вы готовы уделять обучению?\n"
        "1. 1-2 часа\n"
        "2. 3-5 часов\n"
        "3. 6-10 часов\n"
        "4. Более 10 часов"
    )

async def process_available_time(message: types.Message, state: FSMContext):
    data = await state.get_data()
    goal_title = data['goal_title']
    experience = data['experience']
    available_time = message.text
    
    try:
        async with get_db() as session:
            user = await session.execute(select(User).where(User.user_id == message.from_user.id))
            user = user.scalar_one_or_none()

            if not user:
                user = User(user_id=message.from_user.id)
                session.add(user)
                await session.flush()

            # Создаем цель с учетом опыта и доступного времени
            new_goal = Goal(
                user_id=user.user_id,
                title=goal_title,
                user_experience=experience,
                available_time=available_time,
                deadline=calculate_deadline(experience, available_time)
            )
            session.add(new_goal)
            await session.flush()

            # Генерируем план с учетом опыта и времени
            plan = await generate_goal_steps(
                goal_title,
                new_goal.deadline,
                experience,
                available_time
            )

            # Создаем задачи и milestone'ы
            for task_info in plan['tasks']:
                new_task = Task(
                    user_id=user.user_id,
                    goal_id=new_goal.id,
                    title=task_info['title'],
                    description=task_info['description'],
                    due_date=task_info['end_date'],
                    start_date=task_info['start_date'],
                    dependencies=json.dumps(task_info['dependencies']),
                    can_parallel=task_info['can_parallel'],
                    deliverables=json.dumps(task_info['deliverables']),
                    progress_metrics=json.dumps(task_info['progress_metrics']),
                    resources=json.dumps(task_info['resources'])
                )
                session.add(new_task)

            for milestone in plan['milestones']:
                new_milestone = Milestone(
                    goal_id=new_goal.id,
                    title=milestone['title'],
                    expected_date=milestone['date'],
                    success_criteria=json.dumps(milestone['criteria'])
                )
                session.add(new_milestone)

            await session.commit()

            # Формируем ответ с планом
            response = format_goal_plan(plan)
            await message.answer(response)

    except Exception as e:
        logger.error(f"Ошибка при создании цели: {e}", exc_info=True)
        await message.answer("Произошла ошибка при создании плана. Пожалуйста, попробуйте еще раз.")
    
    await state.clear()

def calculate_deadline(experience: str, available_time: str) -> datetime:
    # Логика расчета дедлайна на основе опыта и доступного времени
    base_days = {
        "1": 365,  # Новичок
        "2": 270,  # Базовые знания
        "3": 180,  # Средний уровень
        "4": 90    # Продвинутый
    }
    
    time_multiplier = {
        "1": 1.5,  # 1-2 часа
        "2": 1.0,  # 3-5 часов
        "3": 0.7,  # 6-10 часов
        "4": 0.5   # Более 10 часов
    }
    
    days = base_days.get(experience, 365) * time_multiplier.get(available_time, 1.0)
    return datetime.now() + timedelta(days=days)

def format_goal_plan(plan: dict) -> str:
    """Форматирует план в читаемый вид"""
    response = ["План достижения цели:\n"]
    
    # Добавляем задачи
    for i, task in enumerate(plan['tasks'], 1):
        response.append(f"{i}. {task['title']}")
        response.append(f"   Срок: {task['start_date'].strftime('%d.%m.%Y')} - {task['end_date'].strftime('%d.%m.%Y')}")
        response.append(f"   Результаты: {', '.join(task['deliverables'])}")
        if task['resources']:
            response.append(f"   Ресурсы: {', '.join(task['resources'])}")
        response.append("")
    
    # Добавляем контрольные точки
    response.append("\nКонтрольные точки:")
    for milestone in plan['milestones']:
        response.append(f"📍 {milestone['title']}")
        response.append(f"   Дата: {milestone['date'].strftime('%d.%m.%Y')}")
        response.append(f"   Критерии: {', '.join(milestone['criteria'])}")
        response.append("")
    
    return "\n".join(response)

# Основные команды
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я ваш персональный ассистент. Я могу помочь вам с управлением задачами, "
        "финансами и достижением целей. Просто напишите мне о ваших задачах, "
        "расходах или целях, и я постараюсь помочь.",
        reply_markup=ReplyKeyboardRemove()
    )
    
async def process_message(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Получено сообщение от пользователя {user_id}: {message.text}")
    
    try:
        parsed_data = await parse_message(message.text)
        logger.info(f"Результат парсинга сообщения: {parsed_data}")
        
        if parsed_data['type'] == 'task':
            response = await handle_task(user_id, parsed_data['data'], message.bot)
        elif parsed_data['type'] == 'finance':
            response = await handle_finance(user_id, parsed_data['data'])
        elif parsed_data['type'] == 'goal':
            response = await handle_goal(message, parsed_data['data'])
        else:
            response = "Извините, я не смог точно определить тип вашего запроса. Можете ли вы уточнить, хотите ли вы добавить задачу, записать финансовую операцию или поставить цель?"
        
        logger.info(f"Сгенерирован ответ: {response}")
        await message.answer(response)
    except Exception as e:
        logger.error(f"Ошибка при обработке сообщения: {e}", exc_info=True)
        await message.answer("Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте еще раз позже.")



async def handle_task(user_id: int, task_data: dict, bot) -> str:
    title = task_data['title']
    due_date = datetime.fromisoformat(task_data['due_date'])
    priority = task_data.get('priority', 'medium')
    category = task_data.get('category', 'Общее')

    async with get_db() as session:
        try:
            # Проверяем существование пользователя
            user = await session.execute(select(User).where(User.user_id == user_id))
            user = user.scalar_one_or_none()

            if not user:
                # Если пользователь не существует, создаем его
                user = User(user_id=user_id)
                session.add(user)
                await session.flush()

            # Создаем новую задачу
            new_task = Task(
                user_id=user_id, 
                title=title, 
                due_date=due_date,
                priority=priority,
                category=category
            )
            session.add(new_task)
            await session.commit()
            logging.info(f"New task added: {new_task.title}, due date: {new_task.due_date}")

            # Добавляем джоб в планировщик
            job = scheduler.add_job(
                send_task_reminder,
                trigger='date',
                run_date=new_task.due_date,
                args=[bot, user.user_id, new_task.id]
            )
            new_task.scheduler_job_id = job.id

            await session.commit()
            logging.info(f"New task added: {new_task.title}, due date: {new_task.due_date}")


            return (f"Отлично! Я добавил новую задачу:\n"
                    f"Название: {title}\n"
                    f"Срок: {due_date.strftime('%d.%m.%Y %H:%M')}\n"
                    f"Приоритет: {priority}\n"
                    f"Категория: {category}\n\n"
                    f"Я напомню вам о ней ближе к сроку. Хотите добавить еще что-нибудь?")

        except Exception as e:
            await session.rollback()
            logging.error(f"Ошибка при добавлении задачи: {e}")
            return "Извините, произошла ошибка при добавлении задачи. Пожалуйста, попробуйте еще раз позже."
        
async def handle_finance(user_id: int, finance_data: dict) -> str:
    logger.info(f"Обработка финансовой операции для пользователя {user_id}: {finance_data}")
    async with get_db() as session:
        try:
            user = await session.execute(select(User).where(User.user_id == user_id))
            user = user.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id)
                session.add(user)
                await session.flush()
                logger.info(f"Создан новый пользователь с id {user_id}")

            new_record = FinancialRecord(
                user_id=user_id,
                amount=finance_data['amount'],
                currency=finance_data['currency'],
                category=finance_data['category'],
                description=finance_data['description'],
                type=finance_data['type'],  # 'income' или 'expense'
                is_savings=finance_data.get('is_savings', False)
            )
            session.add(new_record)
            await session.commit()
            logger.info(f"Добавлена новая финансовая запись: {new_record}")

            if finance_data['type'] == 'income':
                return f"Записал доход: {new_record.amount} {new_record.currency} в категории {new_record.category}."
            else:
                return f"Записал расход: {new_record.amount} {new_record.currency} в категории {new_record.category}."

        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при добавлении финансовой записи для пользователя {user_id}: {e}", exc_info=True)
            return "Извините, произошла ошибка при добавлении финансовой записи. Пожалуйста, попробуйте еще раз позже."
        
async def add_regular_payment(user_id: int, payment_data: dict) -> str:
    logger.info(f"Добавление регулярного платежа для пользователя {user_id}: {payment_data}")
    async with get_db() as session:
        try:
            user = await session.get(User, user_id)
            if not user:
                return "Пользователь не найден."

            new_payment = RegularPayment(
                user_id=user_id,
                amount=payment_data['amount'],
                currency=payment_data['currency'],
                category=payment_data['category'],
                description=payment_data['description'],
                frequency=payment_data['frequency'],
                next_payment_date=datetime.fromisoformat(payment_data['next_payment_date'])
            )   
            session.add(new_payment)
            await session.commit()
            logger.info(f"Добавлен новый регулярный платеж: {new_payment}")

            return f"Добавлен регулярный платеж: {new_payment.amount} {new_payment.currency} в категории {new_payment.category}, частота: {new_payment.frequency}."

        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при добавлении регулярного платежа для пользователя {user_id}: {e}", exc_info=True)
            return "Извините, произошла ошибка при добавлении регулярного платежа. Пожалуйста, попробуйте еще раз позже."
        
async def handle_goal(message: types.Message, goal_data: dict) -> str:
    user_id = message.from_user.id
    try:
        async with get_db() as session:
            # Проверяем существование пользователя
            user = await session.execute(select(User).where(User.user_id == user_id))
            user = user.scalar_one_or_none()

            if not user:
                user = User(user_id=user_id)
                session.add(user)
                await session.flush()

            deadline = datetime.fromisoformat(goal_data['deadline'])
            new_goal = Goal(
                user_id=user_id,
                title=goal_data['title'],
                deadline=deadline,
                description=goal_data.get('description', ''),
                user_experience=goal_data.get('experience', 'beginner'),
                available_time=goal_data.get('available_time', 'medium')
            )
            session.add(new_goal)
            await session.flush()

            # Генерируем план задач через GPT
            plan = await generate_goal_steps(
                new_goal.title, 
                deadline,
                new_goal.user_experience,
                new_goal.available_time
            )   
            
            # Создаем задачи из плана
            for task_info in plan['tasks']:
                new_task = Task(
                    user_id=user_id,
                    goal_id=new_goal.id,
                    title=task_info['title'],
                    description=task_info.get('description', ''),
                    due_date=task_info['end_date'],
                    start_date=task_info['start_date'],
                    priority='high',
                    is_completed=False,
                    dependencies=json.dumps(task_info.get('dependencies', [])),
                    can_parallel=task_info.get('can_parallel', False),
                    deliverables=json.dumps(task_info.get('deliverables', [])),
                    progress_metrics=json.dumps(task_info.get('progress_metrics', [])),
                    resources=json.dumps(task_info.get('resources', []))
                )
                session.add(new_task)

            await session.commit()

            # Формируем ответ
            return format_goal_plan(plan)

    except Exception as e:
        logger.error(f"Ошибка при создании цели: {e}", exc_info=True)
        return "Произошла ошибка при создании плана. Пожалуйста, попробуйте еще раз."
    

async def update_task_deadline(task: Task, session):
    """
    Обновляет сроки зависимых задач при изменении срока текущей задачи
    """
    if not task.goal_id:
        return
        
    subsequent_tasks = await session.execute(
        select(Task)
        .where(
            Task.goal_id == task.goal_id,
            Task.order > task.order,
            Task.is_completed == False
        )
        .order_by(Task.order)
    )
    subsequent_tasks = subsequent_tasks.scalars().all()

    if not subsequent_tasks:
        return

    goal = await session.get(Goal, task.goal_id)
    remaining_time = (goal.deadline - datetime.now()).days
    if remaining_time <= 0:
        days_per_task = 1
    else:
        days_per_task = max(1, remaining_time // (len(subsequent_tasks) + 1))

    current_date = datetime.now()
    for subsequent_task in subsequent_tasks:
        current_date += timedelta(days=days_per_task)
        subsequent_task.due_date = min(current_date, goal.deadline)
        session.add(subsequent_task)

# Команды управления задачами
async def show_tasks(message: types.Message):
    user_id = message.from_user.id
    async with get_db() as session:
        tasks = await session.execute(
            select(Task).where(Task.user_id == user_id, Task.is_completed == False)
        )
        tasks = tasks.scalars().all()

    if tasks:
        response = "Ваши текущие задачи:\n" + "\n".join(
            f"ID: {task.id}, Заголовок: {task.title}, Срок: {task.due_date.strftime('%d.%m.%Y %H:%M')}"
            for task in tasks
        )
    else:
        response = "У вас нет текущих задач."

    await message.answer(response)


async def edit_task_command(message: types.Message, state: FSMContext):
    await state.set_state(EditTaskStates.waiting_for_task_id)
    await message.answer("Укажите ID задачи для редактирования. Посмотреть задачи можно командой /tasks.")


async def update_goal_progress(goal_id: int, session):
    """
    Обновляет прогресс цели на основе выполненных задач
    """
    try:
        # Получаем все задачи цели
        tasks = await session.execute(
            select(Task).where(Task.goal_id == goal_id)
        )
        tasks = tasks.scalars().all()
        
        if not tasks:
            return
        
        # Вычисляем процент выполнения
        completed = sum(1 for task in tasks if task.is_completed)
        progress = (completed / len(tasks)) * 100

        # Обновляем прогресс цели
        goal = await session.get(Goal, goal_id)
        if goal:
            goal.progress = progress
            session.add(goal)
            await session.commit()

    except Exception as e:
        logger.error(f"Ошибка при обновлении прогресса цели: {e}")
        await session.rollback()


async def complete_task_command(message: types.Message):
    task_id = message.get_args()
    if not task_id.isdigit():
        await message.answer("Пожалуйста, укажите ID задачи")
        return

    async with get_db() as session:
        task = await session.get(Task, int(task_id))
        if not task:
            await message.answer("Задача не найдена")
            return

        # Проверяем, можно ли выполнить эту задачу (все предыдущие должны быть выполнены)
        if task.goal_id:
            previous_tasks = await session.execute(
                select(Task)
                .where(
                    Task.goal_id == task.goal_id,
                    Task.order < task.order,
                    Task.is_completed == False
                )
            )
            if previous_tasks.scalars().first():
                await message.answer("Сначала необходимо выполнить предыдущие задачи цели")
                return

        task.is_completed = True
        await session.commit()

        # Если задача привязана к цели, обновляем прогресс
        if task.goal_id:
            await update_task_deadline(task, session)
            await update_goal_progress(task.goal_id, session)

        await message.answer(f"Задача '{task.title}' отмечена как выполненная")
# Настройки пользователя
async def set_tone_command(message: types.Message):
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add("Нейтральный", "Дружелюбный", "Строгий")
    await ToneStates.waiting_for_tone.set()
    await message.answer("Выберите тон общения:", reply_markup=keyboard)

async def tone_selected(message: types.Message, state: FSMContext):
    tone_mapping = {"Нейтральный": "neutral", "Дружелюбный": "friendly", "Строгий": "strict"}
    selected_tone = tone_mapping.get(message.text)
    if selected_tone:
        async with get_db() as session:
            user = await session.get(User, message.from_user.id)
            if user:
                user.tone = selected_tone
                await session.commit()
                await message.answer("Тон общения обновлен.", reply_markup=ReplyKeyboardRemove())
            else:
                await message.answer("Пользователь не найден.", reply_markup=ReplyKeyboardRemove())
        await state.clear()
    else:
        await message.answer("Пожалуйста, выберите тон из предложенных вариантов.")

# Обучение
async def learn_command(message: types.Message, state: FSMContext):
    await state.set_state(LearningStates.waiting_for_topic)
    await message.answer("Какую тему вы хотите изучать?")

async def topic_received(message: types.Message, state: FSMContext):
    topic = message.text
    async with get_db() as session:
        user = await session.get(User, message.from_user.id)
        if user:
            user.learning_topic = topic
            user.learning_progress = 0
            await session.commit()
            learning_plan = await generate_personalized_message(user, 'learning_plan', topic=topic)
            await message.answer(learning_plan)
            
            from scheduler import scheduler, check_learning_progress
            scheduler.add_job(check_learning_progress, 'interval', days=1, args=[user.user_id])
        else:
            await message.answer("Пользователь не найден.")
    await state.clear()

async def suggest_resources(message: types.Message):
    user_id = message.from_user.id
    async with get_db() as session:
        user = await session.get(User, user_id)
        if user and user.learning_topic:
            resources = await generate_personalized_message(user, 'learning_resources', topic=user.learning_topic)
            await message.answer(resources)
        else:
            await message.answer("Сначала выберите тему для изучения с помощью команды /learn.")

async def financial_advice_command(message: types.Message):
    user_id = message.from_user.id
    try:
        async with get_db() as session:
            user = await session.get(User, user_id)
            financial_records = await session.execute(
                select(FinancialRecord).where(FinancialRecord.user_id == user_id)
            )
            records = financial_records.scalars().all()
        
        advice = await send_personalized_message(message.bot, user_id, 'financial_advice', records=records)
        await message.answer(advice)
    except Exception as e:
        logger.error(f"Ошибка при генерации финансового совета для пользователя {user_id}: {e}", exc_info=True)
        await message.answer("Извините, произошла ошибка при генерации финансового совета. Пожалуйста, попробуйте позже.")

async def visualize_goals(message: types.Message):
    user_id = message.from_user.id
    async with get_db() as session:
        goals = await session.execute(
            select(Goal).where(Goal.user_id == user_id)
        )
        goals = goals.scalars().all()
    
    # Создание графика
    plt.figure(figsize=(10, 6))
    for goal in goals:
        plt.bar(goal.title, goal.progress)
    plt.title("Прогресс целей")
    plt.xlabel("Цели")
    plt.ylabel("Прогресс (%)")
    
    # Сохранение графика в буфер
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    
    # Отправка графика пользователю
    await message.answer_photo(FSInputFile(buf, filename="goals_progress.png"))

# Регистрация обработчиков
def register_handlers(router: Router):
    router.message.register(start_command, Command("start"))
    router.message.register(show_tasks, Command("tasks"))
    router.message.register(edit_task_command, Command("edit"))
    router.message.register(complete_task_command, Command("complete"))
    router.message.register(set_tone_command, Command("set_tone"))
    router.message.register(learn_command, Command("learn"))
    router.message.register(suggest_resources, Command("resources"))
    router.message.register(financial_advice_command, Command("financial_advice"))
    router.message.register(visualize_goals, Command("visualize_goals"))
    router.message.register(tone_selected, ToneStates.waiting_for_tone)
    router.message.register(topic_received, LearningStates.waiting_for_topic)
    router.message.register(start_goal_creation, Command("new_goal"))
    router.message.register(process_goal_title, GoalCreationStates.waiting_for_title)
    router.message.register(process_experience, GoalCreationStates.waiting_for_experience)
    router.message.register(process_available_time, GoalCreationStates.waiting_for_available_time)

    
    # Обработка всех текстовых сообщений
    router.message.register(process_message, F.content_type == types.ContentType.TEXT)