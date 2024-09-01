# main.py

import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from handlers import (
    handle_data_change, start, request_name, send_intro_message, handle_consent, 
    handle_platform_choice, handle_stage, handle_callback_query, error_handler, 
    show_main_menu, show_personal_cabinet, switch_to_order_number, show_platforms
)
from config import CONNECT, NAME_REQUEST, CONSENT, PLATFORM, ORDER_NUMBER, CONTACT, EMAIL, BIRTHDAY, FINAL, MAIN_MENU, PERSONAL_CABINET, ORDER_NUMBER_PROMPT

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def main() -> None:
    load_dotenv()
    
    application = ApplicationBuilder().token(os.getenv("TOKEN_BOT")).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            CONNECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_intro_message)],
            NAME_REQUEST: [MessageHandler(filters.TEXT & ~filters.COMMAND, request_name)],
            CONSENT: [CallbackQueryHandler(handle_consent)],
            PLATFORM: [CallbackQueryHandler(handle_platform_choice)],
            ORDER_NUMBER_PROMPT: [CallbackQueryHandler(switch_to_order_number, pattern='^switch_state_to_order$'), CallbackQueryHandler(show_platforms, pattern='^choose_platform$')],
            ORDER_NUMBER: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            CONTACT: [MessageHandler(filters.CONTACT, handle_stage)],
            EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            BIRTHDAY: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_stage)],
            FINAL: [
                CallbackQueryHandler(handle_callback_query, pattern='^confirm_yes$|^confirm_no$|^main_menu$|^personal_cabinet$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_data_change)
            ],
            MAIN_MENU: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_main_menu),
                CallbackQueryHandler(handle_callback_query, pattern='^personal_cabinet$|^main_menu$')
            ],
            PERSONAL_CABINET: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, show_personal_cabinet),
                CallbackQueryHandler(handle_callback_query, pattern='^main_menu$')
            ],
        },
        fallbacks=[CommandHandler('start', start)],
    )

    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(handle_callback_query, pattern='^show_photos_|show_pdf_|choose_platform$'))
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
