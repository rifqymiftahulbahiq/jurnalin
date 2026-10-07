from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.fill_service import FillService
from services.validation import validate_user_connection, validate_available_mebs
from database import get_meb_target, get_kejar_account, is_kejar_connected


async def fill_confirm_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id

    is_conn, conn_err = validate_user_connection(user_id)
    if not is_conn:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔐 Hubungkan Kejar.id", callback_data="menu_login")],
            [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
        ])
        if query:
            await query.edit_message_text(conn_err, reply_markup=keyboard)
        return

    is_meb_ok, meb_list, meb_err = validate_available_mebs(user_id)
    if not is_meb_ok:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Sinkron MEB", callback_data="menu_sync")],
            [InlineKeyboardButton("🎯 Target MEB", callback_data="menu_target")],
            [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
        ])
        if query:
            await query.edit_message_text(meb_err, reply_markup=keyboard)
        return

    start_m, end_m = get_meb_target(user_id)

    text = (
        "⚠️ KONFIRMASI PENGISIAN JURNAL\n\n"
        f"Jurnalin akan memproses pengisian jurnal Kejar.id:\n"
        f"• Target Range: MEB {start_m} → MEB {end_m}\n"
        f"• Pembiasaan Harian: Tanggal eligible (<= hari ini)\n"
        f"• Pembiasaan Mingguan: Menggunakan saksi per aktivitas\n"
        f"• 🚫 Jurnal Perilaku: TIDAK DISENTUH\n\n"
        "Apakah kamu yakin ingin melanjutkan pengisian sekarang?"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Ya, Isi Jurnal Sekarang", callback_data="menu_fill_execute")],
        [InlineKeyboardButton("❌ Batal", callback_data="menu_start")]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)


async def fill_execute_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("⏳ Sedang memproses pengisian jurnal Kejar.id secara otomatis...")

    user_id = update.effective_user.id
    fill_service = FillService(telegram_id=user_id, mode="REAL")
    res = await fill_service.execute_fill(date.today())

    create_warn = ""
    if res.get("unvalidated_create_warning"):
        create_warn = (
            "\n⚠️ Automatic CREATE belum diaktifkan karena request Kejar.id belum terbukti. "
            "Sistem tetap aman dalam DRY_RUN / SKIP untuk item tanpa deed_id."
        )

    text = (
        "🎉 PENGISIAN JURNAL SELESAI\n\n"
        f"🎯 Target Range: {res['target_range']}\n\n"
        f"✅ Berhasil: {res['success_count']}\n"
        f"⏭️ Dilewati: {res['skipped_count']}\n"
        f"❌ Gagal: {res['failed_count']}\n"
        f"{create_warn}\n\n"
        "🚫 Jurnal Perilaku: Tidak disentuh."
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Lihat Status", callback_data="menu_status")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)


async def status_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    acc = get_kejar_account(user_id)
    start_m, end_m = get_meb_target(user_id)

    u_name = acc.get("username", "-") if acc else "-"
    conn_status = "Connected ✅" if is_kejar_connected(user_id) else "Disconnected ❌"
    last_sync = acc.get("last_sync_at", "Belum pernah") if acc else "Belum pernah"

    text = (
        "📊 STATUS AKUN & JURNAL\n\n"
        f"👤 Akun Kejar.id: {u_name}\n"
        f"🔐 Status Koneksi: {conn_status}\n"
        f"🎯 Target MEB: MEB {start_m} → MEB {end_m}\n"
        f"🔄 Last Sync: {last_sync}\n"
        f"🔒 Browser Session: Active"
    )

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Sinkron MEB", callback_data="menu_sync")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
