import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import create_or_update_user, ensure_user_settings, save_meb_target, is_kejar_connected, get_kejar_account, get_meb_target
from services.validation import validate_target_range


def main_menu_keyboard(telegram_id: int) -> InlineKeyboardMarkup:
    connected = is_kejar_connected(telegram_id)
    conn_text = "🔐 Hubungkan Kejar.id" if not connected else "✅ Kejar.id Terhubung"

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(conn_text, callback_data="menu_login"),
        ],
        [
            InlineKeyboardButton("🎯 Target MEB", callback_data="menu_target"),
            InlineKeyboardButton("📅 MEB Saya", callback_data="menu_meb_list"),
        ],
        [
            InlineKeyboardButton("🔄 Sinkron MEB", callback_data="menu_sync"),
            InlineKeyboardButton("👀 Preview Isi", callback_data="menu_preview"),
        ],
        [
            InlineKeyboardButton("⚙️ Pengaturan", callback_data="menu_settings"),
            InlineKeyboardButton("📊 Status", callback_data="menu_status"),
        ],
        [
            InlineKeyboardButton("✍️ Isi Jurnal", callback_data="menu_fill_confirm"),
            InlineKeyboardButton("❓ Bantuan", callback_data="menu_help"),
        ],
    ])


async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if not user:
        return

    create_or_update_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name
    )
    ensure_user_settings(user.id)
    context.user_data.clear()

    text = (
        "🤖 JURNALIN\n\n"
        "Halo! 👋 Selamat datang di Jurnalin - Telegram Assistant untuk Kejar.id.\n\n"
        "Saya siap membantu mengelola dan mengantisipasi pengisian jurnal Pembiasaan / MEB kamu secara otomatis & aman.\n\n"
        "Silakan pilih menu di bawah ini:"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(user.id))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(user.id))


async def text_natural_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    msg = update.message.text.strip()
    user_id = update.effective_user.id

    # Pattern: "Isi MEB X sampai MEB Y" or "MEB X - MEB Y" or "Isi MEB X hingga Y"
    pattern = r"(?:isi\s+)?meb\s*(\d+)\s*(?:sampai|hingga|-|to)\s*(?:meb\s*)?(\d+)"
    match = re.search(pattern, msg, re.IGNORECASE)

    if match:
        start_m = int(match.group(1))
        end_m = int(match.group(2))

        valid, err_msg = validate_target_range(start_m, end_m)
        if not valid:
            await update.message.reply_text(err_msg)
            return

        save_meb_target(user_id, start_m, end_m)
        await update.message.reply_text(
            f"🎯 Target MEB berhasil diatur: MEB {start_m} → MEB {end_m}\n\n"
            "Tekan [👀 Preview Isi] untuk melihat pratinjau atau [✍️ Isi Jurnal] untuk melanjutkan.",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        await update.message.reply_text(
            "💡 Perintah tidak dikenali.\n\n"
            "Kamu bisa mengetik seperti: 'Isi MEB 1 sampai MEB 5'\n"
            "atau pilih menu di bawah ini:",
            reply_markup=main_menu_keyboard(user_id)
        )


async def help_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    text = (
        "❓ BANTUAN & PANDUAN JURNALIN\n\n"
        "1. 🔐 Hubungkan Kejar.id: Masukkan username & password Kejar.id kamu.\n"
        "   - Password HANYA digunakan sementara untuk login browser profile.\n"
        "   - Pesan password di Telegram langsung dihapus otomatis.\n\n"
        "2. 🔄 Sinkron MEB: Mengambil data MEB actual dari Kejar.id.\n"
        "3. 🎯 Target MEB: Pilih MEB awal & MEB akhir (MEB 1 - 36).\n"
        "4. 👀 Preview Isi: Lihat simulasi tanggal eligible & aktivitas yang siap diisi.\n"
        "5. ✍️ Isi Jurnal: Jalankan pengisian jurnal secara aman.\n\n"
        "⚠️ Catatan Keamanan:\n"
        "- CAPTCHA / OTP harus diselesaikan manual di browser jika muncul.\n"
        "- 🚫 Jurnal Perilaku TIDAK DISENTUH demi keamanan integritas siswa."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kembali ke Menu Utama", callback_data="menu_start")]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.message:
        await update.message.reply_text(text, reply_markup=keyboard)
