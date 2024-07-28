async def send_long_message(update: Update, context: CallbackContext, message: str) -> None:
    max_length = 4096
    for i in range(0, len(message), max_length):
        await update.message.reply_text(message[i:i + max_length])
        await asyncio.sleep(1)

async def handle_message_6(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    await send_long_message(update, context, messages["info_use"])
    await asyncio.sleep(2)
    user_data[user_id]['stage'] = PLATFORM
    await update.message.reply_text(messages["choose_platform"], reply_markup=ReplyKeyboardMarkup([['Ozon', 'Wildberries']], one_time_keyboard=True))
    return PLATFORM