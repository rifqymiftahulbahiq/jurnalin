import gc
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)
from kejar.auth import login_kejar
from kejar.browser_session import clear_user_cookies
from database import is_kejar_connected, get_kejar_account, set_kejar_account_connected

WAITING_USERNAME, WAITING_PASSWORD = range(2)


async def start_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if is_kejar_connected(user_id):
        acc = get_kejar_account(user_id)
        u_name = acc.get("username", "") if acc else ""
        text = (
            f"✅ Akun Kejar.id kamu ({u_name}) sudah terhubung.\n\n"
            "Pilih opsi di bawah ini:"
        )
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Hubungkan Ulang (Ganti Akun)", callback_data="login_reconnect")],
            [InlineKeyboardButton("🚪 Logout / Putuskan Akun", callback_data="login_logout")],
            [InlineKeyboardButton("⬅️ Kembali", callback_data="menu_start")]
        ])
        await query.edit_message_text(text, reply_markup=keyboard)
        return ConversationHandler.END

    await query.edit_message_text(
        "👤 Masukkan username / NIS / Email Kejar.id kamu:"
    )
    return WAITING_USERNAME


async def reconnect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    user_id = update.effective_user.id
    set_kejar_account_connected(user_id, "", False)
    clear_user_cookies(user_id)
    context.user_data.clear()

    if query:
        await query.edit_message_text(
            "👤 Masukkan username / NIS / Email Kejar.id kamu:"
        )
    return WAITING_USERNAME


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    user_id = update.effective_user.id
    set_kejar_account_connected(user_id, "", False)
    clear_user_cookies(user_id)
    context.user_data.clear()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Hubungkan Akun Baru", callback_data="menu_login")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    text = "🚪 Akun Kejar.id berhasil dikeluarkan / diputuskan."
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    return ConversationHandler.END


async def process_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return WAITING_USERNAME

    username = update.message.text.strip()
    context.user_data["temp_username"] = username

    await update.message.reply_text(
        "🔑 Masukkan password Kejar.id kamu:\n\n"
        "🔒 Keamanan: Pesan password ini akan langsung dihapus otomatis setelah diterima."
    )
    return WAITING_PASSWORD


async def process_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return WAITING_PASSWORD

    user_id = update.effective_user.id
    username = context.user_data.get("temp_username", "")
    password_text = update.message.text.strip()

    # Try deleting telegram message containing password
    try:
        await context.bot.delete_message(
            chat_id=update.effective_chat.id,
            message_id=update.message.message_id
        )
    except Exception:
        pass

    msg_status = await update.effective_chat.send_message(
        "⏳ Sedang menghubungkan ke Kejar.id..."
    )

    # Perform login
    login_result = await login_kejar(user_id, username, password_text, headless=True)

    # Clear memory reference
    del password_text
    gc.collect()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Sinkron MEB", callback_data="menu_sync")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    await msg_status.edit_text(login_result["message"], reply_markup=keyboard)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel_login(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if update.callback_query:
        try:
            await update.callback_query.answer()
        except Exception:
            pass
        await update.callback_query.edit_message_text(
            "❌ Proses login dibatalkan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]])
        )
    elif update.message:
        await update.message.reply_text(
            "❌ Proses login dibatalkan.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]])
        )
    return ConversationHandler.END


def get_login_conversation_handler():
    return ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_login_callback, pattern="^menu_login$"),
            CallbackQueryHandler(reconnect_callback, pattern="^login_reconnect$"),
            CallbackQueryHandler(logout_callback, pattern="^login_logout$")
        ],
        states={
            WAITING_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_username)],
            WAITING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, process_password)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel_login),
            CallbackQueryHandler(cancel_login, pattern="^login_cancel$")
        ],
        allow_reentry=True,
        per_message=False
    )
