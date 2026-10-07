import re
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    create_or_update_user,
    ensure_user_settings,
    save_meb_target,
    is_kejar_connected,
    get_kejar_account,
    get_meb_target,
    get_user_mebs
)
from services.validation import validate_target_range
from services.sync_service import sync_kejar_data
from services.planner import generate_journal_plan


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
        "Silakan pilih menu di bawah atau ketik kalimat bebas seperti:\n"
        "💬 'Tolong isikan jurnal harian MEB 9'"
    )

    if update.message:
        await update.message.reply_text(text, reply_markup=main_menu_keyboard(user.id))
    elif update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=main_menu_keyboard(user.id))


from handlers.login import login_text_handler


async def text_natural_language_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    # Check if user is currently entering login credentials (username/password)
    if await login_text_handler(update, context):
        return

    msg = update.message.text.strip()
    user_id = update.effective_user.id

    # 1. Check Range MEB: "Tolong isikan MEB 1 sampai 5" or "Isi MEB 1 - 5"
    range_pattern = r"(?:tolong\s+)?(?:isikan|isi)\s*(?:jurnal\s+)?(?:harian\s+)?meb\s*(\d+)\s*(?:sampai|hingga|-|s/d|to)\s*(?:meb\s*)?(\d+)"
    # 2. Check Single MEB: "Tolong isikan jurnal harian meb 9" or "Isi MEB 9"
    single_pattern = r"(?:tolong\s+)?(?:isikan|isi)\s*(?:jurnal\s+)?(?:harian\s+)?meb\s*(\d+)"

    match_range = re.search(range_pattern, msg, re.IGNORECASE)
    match_single = re.search(single_pattern, msg, re.IGNORECASE)

    start_m, end_m = None, None

    if match_range:
        start_m = int(match_range.group(1))
        end_m = int(match_range.group(2))
    elif match_single:
        start_m = int(match_single.group(1))
        end_m = start_m

    if start_m is not None and end_m is not None:
        valid, err_msg = validate_target_range(start_m, end_m)
        if not valid:
            await update.message.reply_text(err_msg)
            return

        save_meb_target(user_id, start_m, end_m)

        # Check connection
        if not is_kejar_connected(user_id):
            await update.message.reply_text(
                f"🎯 Target MEB diatur ke: MEB {start_m} → MEB {end_m}\n\n"
                "🔐 Akun Kejar.id belum terhubung. Silakan tekan [🔐 Hubungkan Kejar.id] terlebih dahulu.",
                reply_markup=main_menu_keyboard(user_id)
            )
            return

        # Auto sync if database has no mebs yet
        if not get_user_mebs(user_id):
            await update.message.reply_text("⏳ Memulai auto-sinkronisasi MEB dari Kejar.id...")
            await sync_kejar_data(user_id)

        # Generate dry run plan
        plan = generate_journal_plan(user_id, date.today())

        target_str = f"MEB {start_m}" if start_m == end_m else f"MEB {start_m} → MEB {end_m}"

        lines = [
            "🤖 SIAP MEMPROSES PERINTAH KAMU!\n",
            f"🎯 Target: {target_str}",
            f"📆 Hari Eligible: {plan['total_eligible_days']} hari (<= hari ini)",
            f"⚡ Total Action Rencana: {plan['total_planned_actions']} update\n",
            "📋 Rincian Target:"
        ]
        for m in plan["mebs_detail"]:
            e_dates = m["eligible_dates"]
            d_str = ", ".join([d[5:] for d in e_dates]) if e_dates else "Belum ada tanggal eligible"
            lines.append(f"• {m['label']}: Tanggal {d_str}")

        lines.append("\n🚫 Jurnal Perilaku: Tidak disentuh.")
        lines.append("\nApakah kamu ingin langsung mengisinya sekarang?")

        text = "\n".join(lines)
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Ya, Langsung Isi Jurnal Sekarang", callback_data="menu_fill_execute")],
            [InlineKeyboardButton("❌ Batal", callback_data="menu_start")]
        ])

        await update.message.reply_text(text, reply_markup=keyboard)
    else:
        await update.message.reply_text(
            "💡 Perintah tidak dikenali.\n\n"
            "Kamu bisa mengetik kalimat bebas seperti:\n"
            "• 'Tolong isikan jurnal harian MEB 9'\n"
            "• 'Isi MEB 1 sampai MEB 5'\n\n"
            "Atau pilih menu di bawah ini:",
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
