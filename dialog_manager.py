from aiogram.fsm.state import State, StatesGroup
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from contextlib import contextmanager
from aiogram import types
from aiogram.fsm.context import FSMContext
from datetime import datetime
from message_utils import (
    generate_message, 
    send_personalized_message,
    analyze_user_message
)

class DialogStates(StatesGroup):
    """Состояния диалога с пользователем"""
    discussing_task = State()      # Обсуждение задачи
    analyzing_problem = State()    # Анализ проблемы
    offering_solutions = State()   # Предложение решений
    setting_next_steps = State()   # Определение следующих шагов
    taking_break = State()         # Перерыв в диалоге

class DialogContext:
    """Хранение контекста диалога"""
    def __init__(self):
        self.topic = None           # Тема обсуждения
        self.identified_issues = [] # Выявленные проблемы
        self.proposed_solutions = [] # Предложенные решения
        self.next_steps = []        # Следующие шаги
        self.start_time = None      # Время начала диалога
        self.messages_count = 0     # Количество сообщений в диалоге

async def start_dialog_mode(message: types.Message, state: FSMContext, topic: str):
    """Начинает диалоговый режим с пользователем"""
    dialog_context = DialogContext()
    dialog_context.topic = topic
    dialog_context.start_time = datetime.now()
    
    await state.set_data({"dialog_context": dialog_context})
    await state.set_state(DialogStates.analyzing_problem)
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🤔 Обсудить проблему", callback_data="discuss_problem"),
                InlineKeyboardButton(text="💡 Предложить решение", callback_data="suggest_solution")
            ],
            [
                InlineKeyboardButton(text="📋 Составить план", callback_data="make_plan"),
                InlineKeyboardButton(text="⏸️ Сделать перерыв", callback_data="take_break")
            ],
            [
                InlineKeyboardButton(text="✅ Завершить диалог", callback_data="end_dialog")
            ]
        ]
    )
    
    prompt = f"""
    Пользователь хочет обсудить тему: {topic}
    
    Создай краткое вступительное сообщение, где:
    1. Покажи понимание ситуации
    2. Предложи несколько направлений для обсуждения
    3. Дай понять, что готов слушать и помогать
    
    Сообщение должно быть теплым и открытым к диалогу.
    Не используй формальные фразы типа "Чем могу помочь?"
    """
    
    initial_message = await generate_message(
        user_id=message.from_user.id,
        message_type='dialog_start',
        use_context=True,
        topic=topic
    )
    await message.answer(initial_message, reply_markup=keyboard)

async def handle_dialog_action(callback: types.CallbackQuery, state: FSMContext):
    """Обработчик действий в диалоге"""
    action = callback.data
    state_data = await state.get_data()
    dialog_context: DialogContext = state_data.get("dialog_context")
    
    if not dialog_context:
        await callback.answer("Диалог уже завершен")
        return

    if action == "discuss_problem":
        await state.set_state(DialogStates.analyzing_problem)
        prompt = f"""
        Тема диалога: {dialog_context.topic}
        Выявленные проблемы: {dialog_context.identified_issues}
        
        Создай сообщение, которое:
        1. Задаст 1-2 конкретных вопроса о проблеме
        2. Покажет связь с уже обсужденными моментами
        3. Поможет пользователю глубже разобраться в ситуации
        
        Избегай общих вопросов типа "Расскажите подробнее"
        """
        
    elif action == "suggest_solution":
        await state.set_state(DialogStates.offering_solutions)
        prompt = f"""
        Тема диалога: {dialog_context.topic}
        Выявленные проблемы: {dialog_context.identified_issues}
        
        Предложи решение, которое:
        1. Учитывает конкретные проблемы пользователя
        2. Содержит маленький, выполнимый первый шаг
        3. Опирается на сильные стороны пользователя
        
        Сделай акцент на практичности и достижимости.
        """
        
    elif action == "make_plan":
        await state.set_state(DialogStates.setting_next_steps)
        prompt = f"""
        Тема диалога: {dialog_context.topic}
        Предложенные решения: {dialog_context.proposed_solutions}
        
        Создай сообщение для планирования, которое:
        1. Предложит разбить выбранное решение на конкретные шаги
        2. Спросит о предпочтительных сроках
        3. Уточнит, какая поддержка нужна
        
        Фокус на создании реалистичного, выполнимого плана.
        """
        
    elif action == "take_break":
        await state.set_state(DialogStates.taking_break)
        prompt = f"""
        Тема диалога: {dialog_context.topic}
        Длительность разговора: {(datetime.now() - dialog_context.start_time).minutes} минут
        
        Создай сообщение о перерыве, которое:
        1. Подытожит основные моменты обсуждения
        2. Предложит вернуться к разговору позже
        3. Напомнит о важности отдыха
        
        Сообщение должно быть поддерживающим и оставлять пространство для возвращения к диалогу.
        """
        
    elif action == "end_dialog":
        prompt = f"""
        Тема диалога: {dialog_context.topic}
        Выявленные проблемы: {dialog_context.identified_issues}
        Предложенные решения: {dialog_context.proposed_solutions}
        Следующие шаги: {dialog_context.next_steps}
        
        Создай завершающее сообщение, которое:
        1. Кратко подытожит основные решения и шаги
        2. Выразит уверенность в способностях пользователя
        3. Напомнит, что всегда можно вернуться к обсуждению
        
        Сообщение должно быть мотивирующим, но без излишнего оптимизма.
        """
        await state.clear()
    
    message = await generate_message(prompt)
    await callback.message.answer(message)
    await callback.answer()

async def handle_user_dialog_message(message: types.Message, state: FSMContext):
    """Обработчик сообщений пользователя в диалоге"""
    current_state = await state.get_state()
    state_data = await state.get_data()
    dialog_context: DialogContext = state_data.get("dialog_context")
    
    if not dialog_context or not current_state:
        return
        
    dialog_context.messages_count += 1
    
    # Анализируем сообщение пользователя через GPT для понимания контекста
    analysis_prompt = f"""
    Текущее состояние диалога: {current_state}
    Тема диалога: {dialog_context.topic}
    Сообщение пользователя: {message.text}
    
    Проанализируй сообщение и определи:
    1. Основные проблемы/опасения
    2. Эмоциональное состояние
    3. Готовность к действиям
    4. Нужна ли дополнительная поддержка
    
    Верни результат в формате JSON.
    """
    
    analysis = await analyze_user_message(analysis_prompt)
    
    # Обновляем контекст диалога
    if current_state == DialogStates.analyzing_problem.state:
        dialog_context.identified_issues.append(analysis.get('problems', []))
    elif current_state == DialogStates.offering_solutions.state:
        dialog_context.proposed_solutions.append(analysis.get('proposed_solutions', []))
    elif current_state == DialogStates.setting_next_steps.state:
        dialog_context.next_steps.append(analysis.get('action_items', []))
    
    await state.update_data({"dialog_context": dialog_context})
    
    # Генерируем ответ на основе анализа
    response_prompt = f"""
    Контекст диалога: {dialog_context}
    Анализ сообщения: {analysis}
    
    Создай ответ, который:
    1. Отразит понимание ситуации и эмоций пользователя
    2. Предложит конкретный следующий шаг или вопрос
    3. Сохранит фокус на решении и поддержке
    
    Ответ должен быть кратким и эмпатичным.
    """
    
    response = await generate_message(response_prompt)
    
    # Добавляем инлайн-кнопки в зависимости от контекста
    keyboard = get_context_specific_keyboard(analysis)
    
    await message.answer(response, reply_markup=keyboard)

def get_context_specific_keyboard(analysis: dict) -> InlineKeyboardMarkup:
    """Создает контекстное меню на основе анализа диалога"""
    buttons = []
    
    # Базовые действия всегда доступны
    base_row = [
        InlineKeyboardButton(text="💡 Предложить решение", callback_data="suggest_solution"),
        InlineKeyboardButton(text="✅ Завершить диалог", callback_data="end_dialog")
    ]
    
    # Добавляем специфичные действия на основе анализа
    if analysis.get('needs_emotional_support'):
        buttons.append([
            InlineKeyboardButton(text="🫂 Поддержка", callback_data="emotional_support")
        ])
    
    if analysis.get('ready_for_action'):
        buttons.append([
            InlineKeyboardButton(text="📋 Составить план", callback_data="make_plan")
        ])
    
    if analysis.get('needs_clarification'):
        buttons.append([
            InlineKeyboardButton(text="🤔 Уточнить детали", callback_data="clarify_details")
        ])
    
    buttons.append(base_row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)