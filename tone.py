# tone.py

tone_styles = {
    'neutral': {
        'reminder': "Напоминаю о задаче: '{task_title}'. Пожалуйста, уделите ей внимание.",
        'motivation': "Вы отлично справляетесь! Продолжайте в том же духе.",
        'learning_prompt': "Давайте продолжим ваше обучение по теме '{topic}'.",
        'clarification': "{message}",
        'error': "{message}",
        'task_added': "Отлично! Я добавил новую задачу:\n{details}",
        'finance_added': "Записал {type}: {amount} {currency} в категории {category}.",
        'tone_updated': "Тон общения обновлен на нейтральный."
    },
    'friendly': {
        'reminder': "Привет! 😊 Не забудьте о задаче: '{task_title}'. Я верю в вас!",
        'motivation': "Вы просто молодец! 🌟 Так держать!",
        'learning_prompt': "С удовольствием помогу тебе изучить '{topic}'. Давай начнем! 🚀",
        'clarification': "{message} 😊",
        'error': "{message} 😔",
        'task_added': "Супер! 🎉 Я добавил новую задачу:\n{details}",
        'finance_added': "Отлично! 👍 Записал {type}: {amount} {currency} в категории {category}.",
        'tone_updated': "Прекрасно! 🌟 Теперь мы будем общаться по-дружески!"
    },
    'strict': {
        'reminder': "Требуется выполнить задачу: '{task_title}'. Срочность высокая.",
        'motivation': "Результаты удовлетворительные. Продолжайте выполнение.",
        'learning_prompt': "Приступаем к изучению темы '{topic}'. Время ограничено.",
        'clarification': "{message}",
        'error': "{message}",
        'task_added': "Задача добавлена в систему:\n{details}",
        'finance_added': "Зарегистрирована операция: {type} {amount} {currency}, категория {category}.",
        'tone_updated': "Тон коммуникации установлен на формальный."
    },
    'sarcastic': {
        'reminder': "Ой, смотрите-ка, тут у нас задача '{task_title}' пылится. Может, соизволите обратить на неё внимание? 🙄",
        'motivation': "Вау! Вы действительно что-то сделали! Кто бы мог подумать! 👏",
        'learning_prompt': "О, решили наконец-то заняться '{topic}'? Ну давайте, удивите меня! 🎭",
        'clarification': "Ах, какая неожиданность! {message} 🙃",
        'error': "Упс! {message} Но вы же справитесь, правда? 😏",
        'task_added': "О, какая честь! Новая задача в моей коллекции:\n{details}\nНадеюсь, эта хотя бы будет выполнена... 😏",
        'finance_added': "Ого! {type}: {amount} {currency} в категории {category}. Прям по-взрослому! 💸",
        'tone_updated': "Ну наконец-то кто-то оценил мой искрометный юмор! 🎭"
    },
    'loving_mom': {
        'reminder': "Солнышко моё, помнишь про '{task_title}'? Очень за тебя переживаю! ❤️",
        'motivation': "Какой же ты у меня молодец! Я так тобой горжусь! 🤗",
        'learning_prompt': "Давай вместе разберём '{topic}'! Я всегда рядом и помогу тебе во всём! 💝",
        'clarification': "Родной мой, {message} Всё получится, мы справимся! 💖",
        'error': "Не переживай, сладкий! {message} Всё будет хорошо! 🤗",
        'task_added': "Умничка! Записала твою задачку:\n{details}\nНе забудь покушать как следует! 🍲",
        'finance_added': "Золотце моё, записала твои {type}: {amount} {currency} (категория {category}). Ты у меня такой хозяйственный! 💖",
        'tone_updated': "Теперь буду заботиться о тебе ещё больше, мой хороший! ❤️"
    },
    'buddy': {
        'reminder': "Слышь, братан, помнишь про '{task_title}'? Надо сделать, вопрос серьёзный.",
        'motivation': "Нормально идёшь, брат. Держи планку.",
        'learning_prompt': "Давай разберём '{topic}'. Тема важная, надо вникнуть.",
        'clarification': "Слушай, {message} Разберёмся, не вопрос.",
        'error': "Слышь, {message} Ничего, прорвёмся.",
        'task_added': "Записал твоё дело:\n{details}\nДавай, решим этот вопрос.",
        'finance_added': "По деньгам записал: {type} {amount} {currency} ({category}). Порядок.",
        'tone_updated': "Ну всё, теперь я твой личный братан. Поддержу и подскажу."
    }
}

def get_message(user_tone, message_type, **kwargs):
    """
    Получает сообщение в соответствии с тоном общения пользователя
    
    Args:
        user_tone (str): тон общения ('neutral', 'friendly', 'strict', 'sarcastic', 'loving_mom', 'buddy')
        message_type (str): тип сообщения
        **kwargs: дополнительные параметры для форматирования сообщения
    """
    template = tone_styles.get(user_tone, tone_styles['neutral']).get(message_type)
    if template:
        return template.format(**kwargs)
    return kwargs.get('message', '')