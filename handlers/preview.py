from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from services.planner import generate_journal_plan
from services.validation import validate_user_connection, validate_available_mebs


async def preview_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id

    # Validation
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

    # Generate dry run plan
    plan = generate_journal_plan(user_id, date.today())

    lines = [
        "👀 PREVIEW ISI JURNAL (DRY RUN)\n",
        f"🎯 Target Range: {plan['target_range']}",
        f"📅 Total MEB Ditemukan: {plan['total_mebs']}",
        f"📆 Total Hari Eligible: {plan['total_eligible_days']}",
        f"⚡ Total Rencana Action: {plan['total_planned_actions']}\n",
        "📋 RINCIAN PER MEB:"
    ]

    for m in plan["mebs_detail"]:
        e_dates = m["eligible_dates"]
        d_str = ", ".join([d[5:] for d in e_dates]) if e_dates else "Belum ada tanggal eligible"
        lines.append(
            f"• {m['label']}:\n"
            f"  Tangal Eligible: {d_str}\n"
            f"  Action Harian: {len(e_dates)} update\n"
            f"  Action Mingguan: {'1 update' if e_dates else '0 update'}"
        )

    lines.append("\n⚙️ PENGATURAN TAMBAHAN:")
    lines.append(f"• Puasa Sunnah: {plan['puasa_sunnah']}")
    ref_str = "🟢 ON" if plan["refleksi_mingguan"] else "🔴 OFF"
    lines.append(f"• Refleksi Mingguan: {ref_str}")
    lines.append(f"• {plan['behavior_journal']}")

    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Lanjutkan", callback_data="menu_fill_confirm"),
            InlineKeyboardButton("❌ Batal", callback_data="menu_start")
        ]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_chat:
        await update.effective_chat.send_message(text, reply_markup=keyboard)
