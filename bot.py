import logging
import sys
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from database import init_database

from handlers.start import start_handler, text_natural_language_handler, help_handler
from handlers.login import start_login_callback, reconnect_callback, logout_callback
from handlers.meb import (
    target_meb_menu_handler,
    meb_select_start_handler,
    meb_select_end_handler,
    set_start_meb_callback,
    set_end_meb_callback,
    meb_preset_callback,
    meb_list_handler,
    sync_meb_handler,
)
from handlers.settings import (
    settings_menu_handler,
    toggle_setting_callback,
    puasa_sunnah_menu_handler,
    save_puasa_callback,
    weekly_settings_menu_handler,
    edit_witness_type_handler,
    save_witness_type_callback,
    save_all_witness_callback,
    daily_settings_menu_handler,
)
from handlers.preview import preview_handler
from handlers.journal import fill_confirm_handler, fill_execute_handler, status_menu_handler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("jurnalin.bot")


def build_application() -> Application:
    """
    Builds and configures the Telegram Bot application.
    """
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == "TOKEN_BARU_DI_SINI":
        logger.error("TELEGRAM_BOT_TOKEN belum dikonfigurasi di .env file.")
        sys.exit(1)

    init_database()

    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # 1. Direct Login Callbacks
    app.add_handler(CallbackQueryHandler(start_login_callback, pattern="^menu_login$"))
    app.add_handler(CallbackQueryHandler(reconnect_callback, pattern="^login_reconnect$"))
    app.add_handler(CallbackQueryHandler(logout_callback, pattern="^login_logout$"))

    # 2. Command Handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("help", help_handler))
    app.add_handler(CommandHandler("status", status_menu_handler))
    app.add_handler(CommandHandler("settings", settings_menu_handler))
    app.add_handler(CommandHandler("preview", preview_handler))
    app.add_handler(CommandHandler("fill", fill_confirm_handler))
    app.add_handler(CommandHandler("sync", sync_meb_handler))

    # 3. Callback Query Handlers (Navigation & Menus)
    app.add_handler(CallbackQueryHandler(start_handler, pattern="^menu_start$"))
    app.add_handler(CallbackQueryHandler(help_handler, pattern="^menu_help$"))
    app.add_handler(CallbackQueryHandler(status_menu_handler, pattern="^menu_status$"))
    app.add_handler(CallbackQueryHandler(sync_meb_handler, pattern="^menu_sync$"))

    # MEB Callbacks
    app.add_handler(CallbackQueryHandler(target_meb_menu_handler, pattern="^menu_target$"))
    app.add_handler(CallbackQueryHandler(meb_list_handler, pattern="^menu_meb_list$"))
    app.add_handler(CallbackQueryHandler(meb_select_start_handler, pattern="^meb_select_start$"))
    app.add_handler(CallbackQueryHandler(meb_select_end_handler, pattern="^meb_select_end$"))
    app.add_handler(CallbackQueryHandler(set_start_meb_callback, pattern="^set_start_meb_\\d+$"))
    app.add_handler(CallbackQueryHandler(set_end_meb_callback, pattern="^set_end_meb_\\d+$"))
    app.add_handler(CallbackQueryHandler(meb_preset_callback, pattern="^meb_preset_"))

    # Settings Callbacks
    app.add_handler(CallbackQueryHandler(settings_menu_handler, pattern="^menu_settings$"))
    app.add_handler(CallbackQueryHandler(toggle_setting_callback, pattern="^toggle_"))
    app.add_handler(CallbackQueryHandler(puasa_sunnah_menu_handler, pattern="^set_puasa_menu$"))
    app.add_handler(CallbackQueryHandler(save_puasa_callback, pattern="^save_puasa_\\d+$"))
    app.add_handler(CallbackQueryHandler(weekly_settings_menu_handler, pattern="^set_weekly_menu$"))
    app.add_handler(CallbackQueryHandler(edit_witness_type_handler, pattern="^(edit_w_|edit_witness_)"))
    app.add_handler(CallbackQueryHandler(save_witness_type_callback, pattern="^(save_w_|save_wtype_)"))
    app.add_handler(CallbackQueryHandler(save_all_witness_callback, pattern="^save_wall_"))
    app.add_handler(CallbackQueryHandler(daily_settings_menu_handler, pattern="^set_daily_menu$"))

    # Preview & Fill Callbacks
    app.add_handler(CallbackQueryHandler(preview_handler, pattern="^menu_preview$"))
    app.add_handler(CallbackQueryHandler(fill_confirm_handler, pattern="^menu_fill_confirm$"))
    app.add_handler(CallbackQueryHandler(fill_execute_handler, pattern="^menu_fill_execute$"))

    # 4. Message Handler for natural language text inputs
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_natural_language_handler))

    return app


def main():
    logger.info("Memulai Jurnalin Telegram Bot...")
    app = build_application()
    app.run_polling(drop_pending_updates=False)



if __name__ == "__main__":
    main()