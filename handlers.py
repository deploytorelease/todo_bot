# handlers.py

from aiogram import types, Router, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import ReplyKeyboardMarkup, ReplyKeyboardRemove, FSInputFile
from database import get_db
from models import User, Task, CompletedTask, FinancialRecord, Goal, GoalStep
from ai_module import parse_message, generate_personalized_message
from datetime import datetime
from sqlalchemy import select, func
import logging
import matplotlib.pyplot as plt
import io
from scheduler import send_task_reminder, scheduler
from message_utils import send_personalized_message, get_user, get_task

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

# Основные команды
async def start_command(message: types.Message):
    await message.answer(
        "Привет! Я ваш персональный ассистент. Я могу помочь вам с управлением задачами, "
        "финансами и достижением целей. Просто напишите мне о ваших задачах, "
        "расходах или целях, и я постараюсь помочь.",
        reply_markup=ReplyKeyboardRemove()
    )

async def process_message(message: types.Message, bot):
    user_id = message.from_user.id
    logger.info(f"Получено сообщение от пользователя {user_id}: {message.text}")
    
    try:
        parsed_data = await parse_message(message.text)
        logger.info(f"Результат парсинга сообщения: {parsed_data}")
        
        if parsed_data['type'] == 'task':
            response = await handle_task(user_id, parsed_data['data'], bot)
        elif parsed_data['type'] == 'finance':
            response = await handle_finance(user_id, parsed_data['data'])
        elif parsed_data['type'] == 'goal':
            response = await handle_goal(user_id, parsed_data['data'])
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
                category=finance_data['category'],
                description=finance_data['description']
            )
            session.add(new_record)
            await session.commit()
            logger.info(f"Добавлена новая финансовая запись: {new_record}")

            return f"Записал расход: {new_record.amount} {finance_data.get('currency', 'у.е.')} в категории {new_record.category}."

        except Exception as e:
            await session.rollback()
            logger.error(f"Ошибка при добавлении финансовой записи для пользователя {user_id}: {e}", exc_info=True)
            return "Извините, произошла ошибка при добавлении финансовой записи. Пожалуйста, попробуйте еще раз позже."
        
async def handle_goal(user_id: int, goal_data: dict) -> str:
    try:
        async with get_db() as session:
            user = await session.get(User, user_id)
            if not user:
                user = User(user_id=user_id)
                session.add(user)
                await session.flush()

            new_goal = Goal(
                user_id=user_id,
                title=goal_data['title'],
                deadline=datetime.strptime(goal_data['deadline'], '%d.%m.%Y')
            )
            session.add(new_goal)
            await session.flush()

            for step_description in goal_data['steps']:
                step = GoalStep(goal_id=new_goal.id, description=step_description)
                session.add(step)

            await session.commit()

        plan = await send_personalized_message(None, user_id, 'goal_planning', goal_title=new_goal.title)
        return f"Цель '{new_goal.title}' добавлена. Вот план по её достижению:\n\n{plan}"
    except Exception as e:
        logger.error(f"Ошибка при добавлении цели для пользователя {user_id}: {e}", exc_info=True)
        return "Извините, произошла ошибка при добавлении цели. Пожалуйста, попробуйте еще раз позже."
async def handle_unknown(user_id: int, data: dict) -> str:
    return "Извините, я не совсем понял ваш запрос. Могу я помочь вам с задачами, финансами или целями?"

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
    await state.set_state

async def edit_task_command(message: types.Message, state: FSMContext):
    await state.set_state(EditTaskStates.waiting_for_task_id)
    await message.answer("Укажите ID задачи для редактирования. Посмотреть задачи можно командой /tasks.")

async def task_id_received(message: types.Message, state: FSMContext):
    await state.update_data(task_id=message.text)
    await state.set_state(EditTaskStates.waiting_for_new_title)
    await message.answer("Введите новый заголовок задачи (или 'пропустить').")

async def new_title_received(message: types.Message, state: FSMContext):
    await state.update_data(new_title=None if message.text.lower() == 'пропустить' else message.text)
    await state.set_state(EditTaskStates.waiting_for_new_due_date)
    await message.answer("Введите новую дату и время задачи в формате 'ДД.ММ.ГГГГ ЧЧ:ММ' (или 'пропустить').")

async def new_due_date_received(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    task_id = int(user_data['task_id'])
    new_title = user_data['new_title']
    new_due_date = None if message.text.lower() == 'пропустить' else datetime.strptime(message.text, '%d.%m.%Y %H:%M')

    async with get_db() as session:
        task = await session.get(Task, task_id)
        if task and task.user_id == message.from_user.id:
            if new_title:
                task.title = new_title
            if new_due_date:
                task.due_date = new_due_date
            await session.commit()
            await message.answer("Задача успешно обновлена.")
        else:
            await message.answer("Задача не найдена.")
    await state.clear()

async def complete_task_command(message: types.Message):
    task_description = message.get_args()
    if not task_description:
        await message.answer("Пожалуйста, укажите название задачи или ее описание. Например: /complete купить молоко")
        return

    async with get_db() as session:
        tasks = await session.execute(
            select(Task).where(
                Task.user_id == message.from_user.id,
                Task.is_completed == False,
                Task.title.ilike(f"%{task_description}%")
            )
        )
        tasks = tasks.scalars().all()

        if not tasks:
            await message.answer("Задача не найдена. Проверьте название и попробуйте еще раз.")
            return

        if len(tasks) == 1:
            task = tasks[0]
            task.is_completed = True
            await session.commit()
            await message.answer(f"Задача '{task.title}' отмечена как выполненная.")
        else:
            # Если найдено несколько задач, используем GPT для уточнения
            task_list = "\n".join([f"{i+1}. {task.title} (срок: {task.due_date})" for i, task in enumerate(tasks)])
            clarification_prompt = f"Пользователь хочет отметить задачу как выполненную: '{task_description}'. Найдено несколько подходящих задач:\n{task_list}\nКакую задачу пользователь, скорее всего, имел в виду? Верни только номер задачи."
            
            clarification_response = await parse_message(clarification_prompt)
            
            if 'data' in clarification_response and 'task_number' in clarification_response['data']:
                task_number = int(clarification_response['data']['task_number']) - 1
                if 0 <= task_number < len(tasks):
                    task = tasks[task_number]
                    task.is_completed = True
                    await session.commit()
                    await message.answer(f"Задача '{task.title}' отмечена как выполненная.")
                else:
                    await message.answer("Не удалось определить конкретную задачу. Пожалуйста, уточните название.")
            else:
                await message.answer("Не удалось определить конкретную задачу. Пожалуйста, уточните название.")

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
    
    router.message.register(task_id_received, EditTaskStates.waiting_for_task_id)
    router.message.register(new_title_received, EditTaskStates.waiting_for_new_title)
    router.message.register(new_due_date_received, EditTaskStates.waiting_for_new_due_date)
    router.message.register(tone_selected, ToneStates.waiting_for_tone)
    router.message.register(topic_received, LearningStates.waiting_for_topic)
    
    # Обработка всех текстовых сообщений
    router.message.register(process_message, F.content_type == types.ContentType.TEXT)