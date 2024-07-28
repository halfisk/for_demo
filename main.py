import logging
import os
from dotenv import load_dotenv
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, CallbackQueryHandler, ConversationHandler, filters
from handlers import start, request_name, send_intro_message, handle_consent, handle_platform_choice, handle_stage, error_handler
from config import CONNECT, NAME_REQUEST, CONSENT, PLATFORM, ORDER_NUMBER, CONTACT, EMAIL, BIRTHDAY, FEEDBACK, FINAL

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
    application.add_error_handler(error_handler)

    application.run_polling()

if __name__ == '__main__':
    main()
