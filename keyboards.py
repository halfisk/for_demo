from telegram import InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup

def create_inline_keyboard(buttons):
    return InlineKeyboardMarkup([[InlineKeyboardButton(text, callback_data=callback_data)] for text, callback_data in buttons])

def get_main_menu_keyboard():
    buttons = [
        ("Личный кабинет", "personal_cabinet"),
        # ("Тестовая информация", "test_info")
    ]
    return create_inline_keyboard(buttons)

def get_platform_keyboard(platforms):
    return create_inline_keyboard([(platform["name"], platform["callback_data"]) for platform in platforms])

def get_confirm_keyboard():
    buttons = [
        ("Да", "confirm_yes"),
        # ("Нет", "confirm_no")
    ]
    return create_inline_keyboard(buttons)

def get_change_data_keyboard():
    buttons = [
        ("Имя", "change_name"),
        ("Категория", "change_category"),
        ("Площадка", "change_platform"),
        ("Номер заказа", "change_order_number"),
        ("Контакт", "change_contact"),
        ("Email", "change_email"),
        ("Дата рождения", "change_birthday"),
        ("Назад", "personal_cabinet")
    ]
    return create_inline_keyboard(buttons)

def get_switch_to_order_keyboard():
    buttons = [
        ("Да", "switch_state_to_order"),
        ("Назад", "choose_platform")
    ]
    return create_inline_keyboard(buttons)

def contact_keyboard():
    """Создает клавиатуру с кнопкой для предоставления контакта."""
    contact_button = KeyboardButton("Поделиться контактом", request_contact=True)
    keyboard = ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    return keyboard

def email_keyboard():
    """Создает клавиатуру с кнопкой 'Пропустить' для ввода email."""
    skip_button = KeyboardButton("Пропустить")
    keyboard = ReplyKeyboardMarkup([[skip_button]], one_time_keyboard=True, resize_keyboard=True)
    return keyboard

def confirmation_keyboard():
    """Создает клавиатуру для подтверждения правильности данных."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Да", callback_data="confirm_yes")],
        [InlineKeyboardButton("Нет", callback_data="confirm_no")]
    ])
    return keyboard

def get_personal_cabinet_keyboard():
    """Создает клавиатуру для навигации в личном кабинете."""
    buttons = [
        ("Главное меню", "main_menu"),
    ]
    return create_inline_keyboard(buttons)

def get_connect_keyboard():
    """Создает клавиатуру с кнопкой 'Подключиться'."""
    buttons = [
        ("Подключиться", "connect")
    ]
    return create_inline_keyboard(buttons)

def get_accept_keyboard():
    """Создает клавиатуру с кнопкой 'Принять'."""
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("Принять", callback_data="accept")]
    ])
    return keyboard