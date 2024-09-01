import re
import asyncio
import logging
from telegram.ext import CallbackContext
from telegram import Update

logger = logging.getLogger(__name__)
def is_cyrillic(text):
    return bool(re.match(r'^[А-Яа-яЁё]+$', text))

async def send_messages(message, context, messages_list, parse_mode=None):
    for msg in messages_list:
        await message.reply_text(msg, parse_mode=parse_mode)
        await asyncio.sleep(2)

async def clear_message_cache(context: CallbackContext, query: Update, message_ids: list):
    """Удаляет сообщения, указанные в списке message_ids."""
    chat_id = query.message.chat_id

    for message_id in message_ids:
        try:
            await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
        except Exception as e:
            logger.warning(f"Could not delete message {message_id}: {e}")

    return