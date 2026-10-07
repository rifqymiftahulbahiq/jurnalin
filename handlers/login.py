import gc
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from kejar.auth import login_kejar
from kejar.browser_session import clear_user_cookies
from database import is_kejar_connected, get_kejar_account, set_kejar_account_connected, clear_user_database_data
from services.sync_service import sync_kejar_data

logger = logging.getLogger("jurnalin.login")


async def start_login_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

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
        if query:
            await query.edit_message_text(text, reply_markup=keyboard)
        else:
            await update.effective_chat.send_message(text, reply_markup=keyboard)
        return

    context.user_data["awaiting_input"] = "username"
    text_msg = "👤 Masukkan username / NIS / Email Kejar.id kamu:"
    if query:
        await query.edit_message_text(text_msg)
    else:
        await update.effective_chat.send_message(text_msg)


async def reconnect_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    user_id = update.effective_user.id
    clear_user_database_data(user_id)
    clear_user_cookies(user_id)
    context.user_data.clear()
    context.user_data["awaiting_input"] = "username"

    text_msg = "👤 Masukkan username / NIS / Email Kejar.id kamu yang baru:"
    if query:
        await query.edit_message_text(text_msg)
    else:
        await update.effective_chat.send_message(text_msg)


async def logout_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        try:
            await query.answer()
        except Exception:
            pass

    user_id = update.effective_user.id
    clear_user_database_data(user_id)
    clear_user_cookies(user_id)
    context.user_data.clear()

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Hubungkan Akun Baru", callback_data="menu_login")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    text = "🚪 Akun Kejar.id berhasil dikeluarkan / diputuskan."
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    else:
        await update.effective_chat.send_message(text, reply_markup=keyboard)


async def login_text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """
    Handles username and password text inputs for login.
    Returns True if handled, False otherwise.
    """
    if not update.message or not update.message.text:
        return False

    state = context.user_data.get("awaiting_input")
    if not state:
        return False

    user_id = update.effective_user.id
    text = update.message.text.strip()

    if state == "username":
        context.user_data["temp_username"] = text
        context.user_data["awaiting_input"] = "password"
        await update.message.reply_text(
            "🔑 Masukkan password Kejar.id kamu:\n\n"
            "🔒 Keamanan: Pesan password ini akan langsung dihapus otomatis setelah diterima."
        )
        return True

    elif state == "password":
        context.user_data.pop("awaiting_input", None)
        username = context.user_data.get("temp_username", "")

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

        # Clear old account data before logging in new account
        clear_user_database_data(user_id)
        clear_user_cookies(user_id)

        # Perform login
        login_result = await login_kejar(user_id, username, text, headless=True)

        if login_result.get("success"):
            # Auto-sync data for the newly connected account
            await sync_kejar_data(user_id)

        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Sinkron MEB", callback_data="menu_sync")],
            [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
        ])

        await msg_status.edit_text(login_result["message"], reply_markup=keyboard)
        context.user_data.clear()
        return True

    return False

    return False
