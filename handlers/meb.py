from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import save_meb_target, get_meb_target, get_user_mebs
from services.sync_service import sync_kejar_data
from kejar.meb import eligible_dates, parse_kejar_date, MebPeriod


async def target_meb_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    start_m, end_m = get_meb_target(user_id)

    text = (
        "🎯 PENGATURAN TARGET MEB\n\n"
        f"Target Saat Ini: MEB {start_m} → MEB {end_m}\n"
        "Range MEB didukung: MEB 1 sampai MEB 36.\n\n"
        "Pilih tindakan:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"▶️ MEB Awal: MEB {start_m}", callback_data="meb_select_start"),
            InlineKeyboardButton(f"⏹️ MEB Akhir: MEB {end_m}", callback_data="meb_select_end"),
        ],
        [
            InlineKeyboardButton("⚡ Quick Preset (MEB 1-5)", callback_data="meb_preset_1_5"),
            InlineKeyboardButton("⚡ Quick Preset (MEB 1-10)", callback_data="meb_preset_1_10"),
        ],
        [
            InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")
        ]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)


async def meb_select_start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    # Show buttons for selecting MEB start (1 to 36)
    buttons = []
    row = []
    for i in range(1, 37):
        row.append(InlineKeyboardButton(f"MEB {i}", callback_data=f"set_start_meb_{i}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Batal", callback_data="menu_target")])

    await query.edit_message_text("Pilih MEB Awal:", reply_markup=InlineKeyboardMarkup(buttons))


async def meb_select_end_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    buttons = []
    row = []
    for i in range(1, 37):
        row.append(InlineKeyboardButton(f"MEB {i}", callback_data=f"set_end_meb_{i}"))
        if len(row) == 4:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton("⬅️ Batal", callback_data="menu_target")])

    await query.edit_message_text("Pilih MEB Akhir:", reply_markup=InlineKeyboardMarkup(buttons))


async def set_start_meb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    val = int(query.data.replace("set_start_meb_", ""))

    curr_start, curr_end = get_meb_target(user_id)
    new_end = max(val, curr_end)

    save_meb_target(user_id, val, new_end)
    await target_meb_menu_handler(update, context)


async def set_end_meb_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    val = int(query.data.replace("set_end_meb_", ""))

    curr_start, curr_end = get_meb_target(user_id)
    new_start = min(val, curr_start)

    save_meb_target(user_id, new_start, val)
    await target_meb_menu_handler(update, context)


async def meb_preset_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = update.effective_user.id
    if query.data == "meb_preset_1_5":
        save_meb_target(user_id, 1, 5)
    elif query.data == "meb_preset_1_10":
        save_meb_target(user_id, 1, 10)

    await target_meb_menu_handler(update, context)


async def meb_list_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    mebs = get_user_mebs(user_id)

    if not mebs:
        text = (
            "📅 MEB SAYA\n\n"
            "⚠️ Belum ada data MEB tersimpan.\n"
            "Silakan tekan tombol [🔄 Sinkron MEB] untuk mengambil data MEB actual dari Kejar.id."
        )
    else:
        today = date.today()
        lines = ["📅 DAFTAR MEB TERSINKRON:\n"]
        for m in mebs:
            s_d = parse_kejar_date(m["start_date"])
            e_d = parse_kejar_date(m["end_date"])

            status_str = "❓ Tidak diketahui"
            if s_d and e_d:
                m_obj = MebPeriod(
                    id=m.get("kejar_id", ""),
                    report_period_id=m.get("report_period_id", ""),
                    number=m["meb_number"],
                    label=m.get("label", f"MEB {m['meb_number']}"),
                    start_date=s_d,
                    end_date=e_d,
                    school_week=m.get("school_week", ""),
                    is_matrikulasi=bool(m.get("is_matrikulasi", 0))
                )
                db_status = m.get("completion_status", "BELUM LENGKAP")
                e_dates = eligible_dates(m_obj, today)

                if db_status == "SUDAH LENGKAP":
                    status_str = "🟢 SUDAH LENGKAP (Telah Ditandatangani)"
                elif db_status == "BELUM DIBUKA":
                    status_str = "🔒 BELUM DIBUKA (Belum dibuka oleh sekolah)"
                elif today < s_d:
                    status_str = "⏳ BELUM DIMULAI"
                elif e_dates:
                    status_str = f"🟡 BELUM LENGKAP ({len(e_dates)} hari eligible perlu diisi)"
                else:
                    status_str = "🟢 SUDAH LENGKAP"

            label_name = m.get('label') or f"MEB {m.get('meb_number')}"
            lines.append(
                f"• {label_name} ({m['start_date'][:10]} s/d {m['end_date'][:10]})\n"
                f"  Status: {status_str}"
            )
        text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Sinkron Ulang", callback_data="menu_sync")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)


async def sync_meb_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("⏳ Sedang menyinkronkan data MEB dari Kejar.id...")

    user_id = update.effective_user.id
    res = await sync_kejar_data(user_id)

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📅 Lihat MEB Saya", callback_data="menu_meb_list")],
        [InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")]
    ])

    if query:
        await query.edit_message_text(res["message"], reply_markup=keyboard)
