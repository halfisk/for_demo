import asyncio
import logging
import re
from telegram import InputMediaPhoto, Update, InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import CallbackContext
from qr_codes import get_product_category
from utils import is_cyrillic, send_messages
from config import CONNECT, NAME_REQUEST, CONSENT, PLATFORM, ORDER_NUMBER, CONTACT, EMAIL, BIRTHDAY, FINAL, messages, photo_paths, category_cases, platforms, pdf_paths

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
        await update.message.reply_text("Пожалуйста, введите свое имя на русском языке.")
        return NAME_REQUEST
    
    return await send_intro_message(update, context)

async def send_intro_message(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    user_info = user_data[user_id]

    if not is_cyrillic(user_info['name']):
        await update.message.reply_text("Пожалуйста, введите свое имя на русском языке.")
        return NAME_REQUEST

    # await send_video(update, context)

    intro_message = get_intro_message(user_info)
    await send_messages(update.message, context, [
        intro_message, 
        messages["subscribe"].format(category=category_cases.get(user_info['category'])), 
        messages["friendship"], 
        messages["questions"]
    ], parse_mode='HTML')

    return await request_consent(update, context)

# async def send_video(update: Update, context: CallbackContext) -> None:
#     video_path = 'video/preview/tests.mp4'
#     try:
#         with open(video_path, 'rb') as video_file:
#             await context.bot.send_video(
#                 chat_id=update.effective_chat.id, 
#                 video=video_file, 
#                 caption=messages["video"]
#             )
#     except Exception as e:
#         logger.error(f"Error sending video: {e}")
#         await update.message.reply_text("Произошла ошибка при отправке видео. Пожалуйста, попробуйте позже.")

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

    try:
        await query.message.delete()
    except Exception as e:
        logger.warning(f"Could not delete message {query.message.message_id}: {e}")

    await query.message.reply_text(
        "Спасибо за ваше согласие. Теперь выберите платформу, на которой приобретали нашу продукцию.",
        reply_markup=generate_platform_buttons()
    )
    return PLATFORM

def generate_platform_buttons():
    buttons = [[InlineKeyboardButton(platform["name"], callback_data=platform["callback_data"])] for platform in platforms]
    return InlineKeyboardMarkup(buttons)

async def handle_platform_choice(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    platform = query.data
    user_data[user_id]['platform'] = platform
    await query.answer()

    await query.message.reply_text(messages["order_number_request"])
    logger.info(f"Platform chosen: {platform}")

    try:
        await query.message.delete() 
    except Exception as e:
        logger.warning(f"Could not delete message {query.message.message_id}: {e}")

    logger.info(f"Sending platform photos for: {platform}")
    await send_platform_photos(context, query, platform)
    
    user_data[user_id]['stage'] = ORDER_NUMBER
    return ORDER_NUMBER

async def send_platform_photos(context: CallbackContext, query: Update, platform: str):
    photos = photo_paths.get(platform, [])
    if photos:
        media_group = [InputMediaPhoto(open(photo, 'rb')) for photo in photos]
        try:
            messages_list = await context.bot.send_media_group(
                chat_id=query.message.chat_id,
                media=media_group
            )
            message_ids = [msg.message_id for msg in messages_list]
            logger.info(f"Sent photos: {message_ids}")
        except Exception as e:
            logger.error(f"Error sending photos: {e}")
            await query.message.reply_text("Произошла ошибка при отправке фото. Пожалуйста, попробуйте позже.")
            return

        user_data[query.from_user.id]['instruction_message_ids'] = message_ids

        switch_message = await query.message.reply_text(
            "Вы можете переключиться между фотографиями и PDF-файлом.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Показать PDF", callback_data=f"show_pdf_{platform}")],
                [InlineKeyboardButton("Назад", callback_data="choose_platform")]
            ])
        )
        user_data[query.from_user.id]['instruction_message_ids'].append(switch_message.message_id)
        logger.info("Displayed switch options")
    else:
        await query.message.reply_text("На данный момент у нас нет инструкций для выбранной платформы.")
        logger.info("No instructions available for the chosen platform")
    
    # await query.message.reply_text(messages["order_number_prompt"])
    logger.info("Displayed order number prompt")

async def show_pdf(context: CallbackContext, query: Update, platform: str):
    pdf_path = pdf_paths.get(platform)
    if pdf_path:
        try:
            message_ids = user_data[query.from_user.id].get('instruction_message_ids', [])
            for message_id in message_ids:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
                except Exception as e:
                    logger.warning(f"Could not delete message {message_id}: {e}")

            with open(pdf_path, 'rb') as pdf_file:
                message = await context.bot.send_document(
                    chat_id=query.message.chat_id,
                    document=pdf_file
                )
                message_id = message.message_id
                logger.info(f"Sent PDF: {message_id}")
        except Exception as e:
            logger.error(f"Error sending PDF: {e}")
            await query.message.reply_text("Произошла ошибка при отправке PDF. Пожалуйста, попробуйте позже.")
            return

        user_data[query.from_user.id]['instruction_message_ids'] = [message_id]

        switch_message = await query.message.reply_text(
            "Вы можете переключиться между фотографиями и PDF-файлом.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Показать фото", callback_data=f"show_photos_{platform}")],
                [InlineKeyboardButton("Назад", callback_data="choose_platform")]
            ])
        )
        user_data[query.from_user.id]['instruction_message_ids'].append(switch_message.message_id)
    else:
        await query.message.reply_text("На данный момент у нас нет инструкций для выбранной платформы в формате PDF.")
    
    # Display order number prompt
    await query.message.reply_text(messages["order_number_prompt"])
    logger.info("Displayed order number prompt")

async def show_photos(context: CallbackContext, query: Update, platform: str):
    photos = photo_paths.get(platform, [])
    if photos:
        media_group = [InputMediaPhoto(open(photo, 'rb')) for photo in photos]
        try:
            message_ids = user_data[query.from_user.id].get('instruction_message_ids', [])
            for message_id in message_ids:
                try:
                    await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
                except Exception as e:
                    logger.warning(f"Could not delete message {message_id}: {e}")

            messages_list = await context.bot.send_media_group(
                chat_id=query.message.chat_id,
                media=media_group
            )
            message_ids = [msg.message_id for msg in messages_list]  
            logger.info(f"Sent photos: {message_ids}")
        except Exception as e:
            logger.error(f"Error sending photos: {e}")
            await query.message.reply_text("Произошла ошибка при отправке фото. Пожалуйста, попробуйте позже.")
            return

        user_data[query.from_user.id]['instruction_message_ids'] = message_ids

        switch_message = await query.message.reply_text(
            "Вы можете переключиться между фотографиями и PDF-файлом.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Показать PDF", callback_data=f"show_pdf_{platform}")],
                [InlineKeyboardButton("Назад", callback_data="choose_platform")]
            ])
        )
        user_data[query.from_user.id]['instruction_message_ids'].append(switch_message.message_id)
    else:
        await query.message.reply_text("На данный момент у нас нет инструкций для выбранной платформы.")
    
    # Display order number prompt
    await query.message.reply_text(messages["order_number_prompt"])
    logger.info("Displayed order number prompt")

async def handle_callback_query(update: Update, context: CallbackContext) -> int:
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    logger.info(f"Callback query data: {query.data}")

    if query.data == "choose_platform":
        logger.info("Choosing platform")
        await show_platforms(query, context)
        return PLATFORM
    elif query.data.startswith('show_photos_'):
        platform = query.data.split('_')[-1]
        logger.info(f"Showing photos for platform: {platform}")
        await show_photos(context, query, platform)
        return PLATFORM
    elif query.data.startswith('show_pdf_'):
        platform = query.data.split('_')[-1]
        logger.info(f"Showing PDF for platform: {platform}")
        await show_pdf(context, query, platform)
        return PLATFORM
    else:
        return await handle_platform_choice(update, context)

async def show_platforms(query: Update, context: CallbackContext):
    user_id = query.from_user.id
    
    if 'instruction_message_ids' in user_data[user_id]:
        for message_id in user_data[user_id]['instruction_message_ids']:
            try:
                await context.bot.delete_message(chat_id=query.message.chat_id, message_id=message_id)
            except Exception as e:
                logger.warning(f"Could not delete message {message_id}: {e}")
        user_data[user_id].pop('instruction_message_ids', None)

    order_number_request_message_id = user_data[user_id].get('order_number_request_message_id')
    if order_number_request_message_id:
        try:
            await context.bot.delete_message(chat_id=query.message.chat_id, message_id=order_number_request_message_id)
        except Exception as e:
            logger.warning(f"Could not delete message {order_number_request_message_id}: {e}")

    await query.message.reply_text(
        "Выберите платформу, на которой приобретали нашу продукцию.",
        reply_markup=generate_platform_buttons()
    )
    logger.info("Displayed platform options")
    return PLATFORM

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
                # messages["feedback_form"]
            ], parse_mode='HTML')
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
    if isinstance(context.error, Exception):
        try:
            if update and update.message:
                update.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
            elif update and update.callback_query:
                update.callback_query.message.reply_text("Произошла ошибка. Пожалуйста, попробуйте позже.")
        except Exception as e:
            logger.error(f"Error sending error message: {e}")