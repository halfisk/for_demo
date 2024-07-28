import re
import asyncio

def is_cyrillic(text):
    return bool(re.match(r'^[А-Яа-яЁё]+$', text))

async def send_messages(message, context, messages_list, parse_mode=None):
    for msg in messages_list:
        await message.reply_text(msg, parse_mode=parse_mode)
        await asyncio.sleep(2)
