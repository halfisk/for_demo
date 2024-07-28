import asyncio
import logging
import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext
from qr_codes import get_product_category
from utils import is_cyrillic, send_messages
from config import CONNECT, NAME_REQUEST, CONSENT, PLATFORM, ORDER_NUMBER, CONTACT, EMAIL, BIRTHDAY, FINAL, messages, photo_paths

logger = logging.getLogger(__name__)

user_data = {}

async def start(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    args = context.args
    category = get_product_category(args[0]) if args else 'Unknown category'

    user_data[user_id] = {
        'name': update.message.from_user.first_name, 
        'category': category
    }

    await update.message.reply_text(
        messages['welcome'],
        reply_markup=ReplyKeyboardMarkup([['Подключиться']], one_time_keyboard=True)
    )
    
    return CONNECT

async def request_name(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_data[user_id]['name'] = update.message.text

    if not is_cyrillic(user_data[user_id]['name']):
        await update.message.reply_text("Пожалуйста, введите свое имя на кириллице.")
        return NAME_REQUEST
    
    return await send_intro_message(update, context)

async def send_intro_message(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_info = user_data[user_id]

    if not is_cyrillic(user_info['name']):
        await update.message.reply_text("Пожалуйста, введите свое имя на кириллице.")
        return NAME_REQUEST

    await send_video(update, context)

    intro_message = get_intro_message(user_info)
    await send_messages(update.message, context, [
        intro_message, 
        messages["subscribe"].format(category=user_info['category']), 
        messages["friendship"], 
        messages["questions"]
    ], parse_mode='HTML')

    return await request_consent(update, context)

async def send_video(update: Update, context: CallbackContext) -> None:
    video_path = 'video/preview/tests.mp4'
    try:
        with open(video_path, 'rb') as video_file:
            await context.bot.send_video(
                chat_id=update.effective_chat.id, 
                video=video_file, 
                caption=messages["video"]
            )
    except Exception as e:
        logger.error(f"Error sending video: {e}")
        await update.message.reply_text("Произошла ошибка при отправке видео. Пожалуйста, попробуйте позже.")

def get_intro_message(user_info):
    if user_info['category'] == 'Постельное белье':
        return messages["intro_bed_linen"].format(name=user_info['name'], category=user_info['category'])
    elif user_info['category'] == 'Полотенца':
        return messages["intro_towel"].format(name=user_info['name'], category=user_info['category'])
    elif user_info['category'] == 'Пледы':
        return messages["intro_blanket"].format(name=user_info['name'], category=user_info['category'])
    return ""

async def request_consent(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_data[user_id]['stage'] = CONSENT

    await update.message.reply_text(messages["info_use"])
    await asyncio.sleep(2)

    consent_file = 'documents/soglasie.pdf'
    try:
        with open(consent_file, 'rb') as file:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file)
    except Exception as e:
        logger.error(f"Error sending consent file: {e}")
        await update.message.reply_text("Произошла ошибка при отправке файла. Пожалуйста, попробуйте позже.")
        return PLATFORM

    await update.message.reply_text(
        "Пожалуйста, ознакомьтесь с согласием на обработку данных. Нажмите 'Принять', если вы согласны с условиями.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Принять", callback_data='accept')]])
    )
    
    return CONSENT

async def handle_consent(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    # Удаление сообщения с кнопкой
    await query.message.delete()

    await query.message.reply_text(
        "Спасибо за ваше согласие. Теперь выберите платформу, на которой приобретали нашу продукцию.",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("Ozon", callback_data='Ozon')],
            [InlineKeyboardButton("Wildberries", callback_data='Wildberries')]
        ])
    )
    return PLATFORM

async def handle_platform_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    user_data[user_id]['platform'] = query.data
    await query.answer()

    await query.message.reply_text(messages["order_number_request"])

    photo_path = photo_paths.get(query.data)
    if photo_path:
        try:
            with open(photo_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=update.effective_chat.id, 
                    photo=photo_file, 
                    caption=messages.get("order_number_instructions", "Инструкция по поиску номера заказа.")
                )
        except Exception as e:
            logger.error(f"Error sending photo: {e}")
            await query.message.reply_text("Произошла ошибка при отправке фото. Пожалуйста, попробуйте позже.")
            return PLATFORM

    await query.message.reply_text(messages["order_number_prompt"])
    user_data[user_id]['stage'] = ORDER_NUMBER
    return ORDER_NUMBER

async def handle_stage(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    stage = user_data[user_id].get('stage', CONNECT)

    if stage == ORDER_NUMBER:
        return await request_contact(update, context)
    elif stage == CONTACT:
        return await request_email(update, context)
    elif stage == EMAIL:
        return await request_birthday(update, context)
    elif stage == BIRTHDAY:
        return await handle_birthday(update, context)

async def request_contact(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_data[user_id]['order_number'] = update.message.text
    await update.message.reply_text(messages["contact_request"])
    await asyncio.sleep(2)
    
    contact_button = KeyboardButton("Поделиться контактом", request_contact=True)
    await update.message.reply_text(
        messages["contact_button"], 
        reply_markup=ReplyKeyboardMarkup([[contact_button]], one_time_keyboard=True, resize_keyboard=True)
    )
    
    user_data[user_id]['stage'] = CONTACT
    return CONTACT

async def request_email(update: Update, context: CallbackContext) -> int:
    if update.message.contact:
        user_id = update.message.from_user.id
        user_data[user_id]['contact'] = update.message.contact.phone_number

        await update.message.reply_text(
            messages["email_request"],
            reply_markup=ReplyKeyboardMarkup([['Пропустить']], one_time_keyboard=True, resize_keyboard=True)
        )
        user_data[user_id]['stage'] = EMAIL
        return EMAIL
    
    await update.message.reply_text("Пожалуйста, используйте кнопку 'Поделиться контактом' для отправки номера телефона.")
    return CONTACT

async def request_birthday(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    if update.message.text.lower() == 'пропустить':
        user_data[user_id]['email'] = 'Не указано'
    else:
        email = update.message.text
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            user_data[user_id]['email'] = email
        else:
            await update.message.reply_text("Некорректный email адрес. Пожалуйста, введите корректный адрес электронной почты или нажмите 'Пропустить'.")
            return EMAIL

    await update.message.reply_text(messages["birthday_request"], reply_markup=ReplyKeyboardRemove())
    user_data[user_id]['stage'] = BIRTHDAY
    return BIRTHDAY

async def handle_birthday(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    birthday = update.message.text
    try:
        day, month, year = map(int, birthday.split('.'))
        if 1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2100:
            user_data[user_id]['birthday'] = birthday
            await send_messages(update.message, context, [
                messages["feedback"],
                messages["feedback_form"]
            ])
            user_data[user_id]['stage'] = FINAL
            await asyncio.sleep(2)
            await update.message.reply_text(messages["thank_you"])

            user_info = user_data.get(user_id)
            summary = (
                f"Имя: {user_info['name']}\n"
                f"Категория: {user_info['category']}\n"
                f"Площадка: {user_info['platform']}\n"
                f"Номер заказа: {user_info['order_number']}\n"
                f"Контакт: {user_info['contact']}\n"
                f"Email: {user_info['email']}\n"
                f"Дата рождения: {user_info['birthday']}\n"
            )
            await update.message.reply_text(f"Ваша информация:\n{summary}")
            return FINAL
        else:
            raise ValueError
    except ValueError:
        await update.message.reply_text("Некорректная дата. Пожалуйста, введите дату в формате ДД.ММ.ГГГГ.")
        return BIRTHDAY

def error_handler(update: Update, context: CallbackContext) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
