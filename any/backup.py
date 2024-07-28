import logging
import asyncio
import re
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler, CallbackQueryHandler
from dotenv import load_dotenv
import os

from qr_codes import get_product_category
from dict_messages import messages

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

(
    CONNECT, NAME_REQUEST, CONSENT, PLATFORM, ORDER_NUMBER, CONTACT, EMAIL, BIRTHDAY, FEEDBACK, FINAL
) = range(10)

user_data = {}

photo_paths = {
    'Ozon': 'photo/instructions/ozon_instruction.jpg',
    'Wildberries': 'photo/instructions/wildberries_instruction.png'
}

def is_cyrillic(text):
    return bool(re.match(r'^[А-Яа-яЁё]+$', text))

async def start(update: Update, context: CallbackContext) -> int:
    args = context.args
    category = 'Unknown category'
    if args:
        category = get_product_category(args[0])
    
    user_id = update.message.from_user.id
    user_data[user_id] = {'name': update.message.from_user.first_name, 'category': category}
    
    await update.message.reply_text(
        messages['welcome'],
        reply_markup=ReplyKeyboardMarkup([['Подключиться']], one_time_keyboard=True)
    )
    
    return CONNECT

async def connect(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_info = user_data.get(user_id)

    if not is_cyrillic(user_info['name']):
        await update.message.reply_text("Пожалуйста, введите свое имя на кириллице.")
        return NAME_REQUEST

    video_path = 'video/preview/tests.mp4'
    try:
        with open(video_path, 'rb') as video_file:
            await context.bot.send_video(chat_id=update.effective_chat.id, video=video_file, caption=messages["video"])
    except Exception as e:
        logger.error(f"Error sending video: {e}")
        await update.message.reply_text("Произошла ошибка при отправке видео. Пожалуйста, попробуйте позже.")
        return CONNECT
    
    if user_info['category'] == 'Постельное белье':
        intro_message = messages["intro_bed_linen"].format(name=user_info['name'], category=user_info['category'])
    elif user_info['category'] == 'Полотенца':
        intro_message = messages["intro_towel"].format(name=user_info['name'], category=user_info['category'])
    elif user_info['category'] == 'Пледы':
        intro_message = messages["intro_blanket"].format(name=user_info['name'], category=user_info['category'])
    else:
        pass

    await send_messages(update.message, context, [intro_message, 
                                                  messages["subscribe"].format(category=user_info['category']), 
                                                  messages["friendship"], 
                                                  messages["questions"]], 
                                                  parse_mode='HTML')
    return await handle_message_6(update, context)

async def send_messages(message, context: CallbackContext, messages_list: list, parse_mode=None) -> None:
    for msg in messages_list:
        await message.reply_text(msg, parse_mode=parse_mode)
        await asyncio.sleep(2)

async def name_request(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_data[user_id]['name'] = update.message.text

    if not is_cyrillic(user_data[user_id]['name']):
        await update.message.reply_text("Пожалуйста, введите свое имя на кириллице.")
        return NAME_REQUEST
    
    return await connect(update, context)

async def handle_message_6(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    await update.message.reply_text(messages["info_use"])
    await asyncio.sleep(2)
    user_data[user_id]['stage'] = CONSENT

    consent_file = 'documents/soglasie.pdf'  
    try:
        with open(consent_file, 'rb') as file:
            await context.bot.send_document(chat_id=update.effective_chat.id, document=file)
    except Exception as e:
        logger.error(f"Error sending consent file: {e}")
        await update.message.reply_text("Произошла ошибка при отправке файла. Пожалуйста, попробуйте позже.")
        return PLATFORM

    keyboard = [[InlineKeyboardButton("Принять", callback_data='accept')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Пожалуйста, ознакомьтесь с согласием на обработку данных. Нажмите 'Принять', если вы согласны с условиями.", reply_markup=reply_markup)
    
    return CONSENT

async def handle_consent(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == 'accept':
        await query.message.reply_text("Спасибо за ваше согласие. Теперь выберите платформу, на которой приобретали нашу продукцию.")
        return await show_platform_selection(query, context)

async def show_platform_selection(query: Update, context: CallbackContext) -> int:
    keyboard = [
        [InlineKeyboardButton("Ozon", callback_data='Ozon')],
        [InlineKeyboardButton("Wildberries", callback_data='Wildberries')]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(messages["choose_platform"], reply_markup=reply_markup)
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
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo_file, caption=messages["order_number_instructions"])
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

    elif stage == CONTACT:
        if update.message.contact:
            user_data[user_id]['contact'] = update.message.contact.phone_number
            await update.message.reply_text(
                messages["email_request"],
                reply_markup=ReplyKeyboardMarkup([['Пропустить']], one_time_keyboard=True, resize_keyboard=True)
            )
            user_data[user_id]['stage'] = EMAIL
            return EMAIL
        else:
            await update.message.reply_text("Пожалуйста, используйте кнопку 'Поделиться контактом' для отправки номера телефона.")
            return CONTACT

    elif stage == EMAIL:
        if update.message.text.lower() == 'пропустить':
            user_data[user_id]['email'] = 'Не указано'
            await update.message.reply_text(messages["birthday_request"], reply_markup=ReplyKeyboardRemove())
            user_data[user_id]['stage'] = BIRTHDAY
            return BIRTHDAY
        
        email = update.message.text
        if re.match(r"[^@]+@[^@]+\.[^@]+", email):
            user_data[user_id]['email'] = email
            await update.message.reply_text(messages["birthday_request"], reply_markup=ReplyKeyboardRemove())
            user_data[user_id]['stage'] = BIRTHDAY
            return BIRTHDAY
        else:
            await update.message.reply_text("Некорректный email адрес. Пожалуйста, введите корректный адрес электронной почты или нажмите 'Пропустить'.")
            return EMAIL

    elif stage == BIRTHDAY:
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

def error(update: Update, context: CallbackContext) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)

def main() -> None:
    load_dotenv()

    application = ApplicationBuilder().token(os.getenv("TOKEN_BOT")).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONNECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, connect)],
            NAME_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, name_request)],
            CONSENT: [CallbackQueryHandler(handle_consent)],
            PLATFORM: [CallbackQueryHandler(handle_platform_choice)],
            ORDER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            CONTACT: [MessageHandler(filters.CONTACT, handle_stage)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            FEEDBACK: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            FINAL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.add_error_handler(error)

    application.run_polling()

if __name__ == '__main__':
    main()
