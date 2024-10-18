# tone.py

tone_styles = {
    'neutral': {
        'reminder': "Напоминаю о задаче: '{task_title}'. Пожалуйста, уделите ей внимание.",
        'motivation': "Вы отлично справляетесь! Продолжайте в том же духе.",
        'learning_prompt': "Давайте продолжим ваше обучение по теме '{topic}'.",
    },
    'friendly': {
        'reminder': "Привет! 😊 Не забудьте о задаче: '{task_title}'. Я верю в вас!",
        'motivation': "Ты молодец! Продолжай в том же духе!",
        'learning_prompt': "С удовольствием помогу тебе изучить '{topic}'. Давай начнем!",
    },
    'strict': {
        'reminder': "Напоминаю: задача '{task_title}' ожидает вашего внимания.",
        'motivation': "Пора действовать. Не откладывайте на потом.",
        'learning_prompt': "Приступим к изучению '{topic}'. Не теряйте время.",
    }
}

def get_message(user_tone, message_type, **kwargs):
    template = tone_styles.get(user_tone, tone_styles['neutral']).get(message_type)
    if template:
        return template.format(**kwargs)
    else:
        return ""