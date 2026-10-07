from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database import (
    get_settings,
    update_setting,
    get_weekly_activity_settings,
    save_weekly_activity_setting,
    get_daily_activity_settings,
    save_daily_activity_setting
)


async def settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    st = get_settings(user_id)

    puasa = st.get("puasa_sunnah", "Melaksanakan 2 hari")
    refleksi = "🟢 ON" if st.get("refleksi_mingguan") else "🔴 OFF"
    internship = "🟢 YA (PKL)" if st.get("is_internship") else "🔴 TIDAK"
    haid_status = "🔴 Sedang Haid" if st.get("is_haid") else "🟢 Normal"
    autosign = "🟢 ON" if st.get("auto_sign", 1) else "🔴 OFF"

    text = (
        "⚙️ PENGATURAN JURNALIN\n\n"
        "Sesuaikan preferensi pengisian jurnal kamu:\n\n"
        f"• Puasa Sunnah: {puasa}\n"
        f"• Refleksi Mingguan: {refleksi}\n"
        f"• Status Internship / PKL: {internship}\n"
        f"• Kondisi Siswi: {haid_status}\n"
        f"• Auto Tanda Tangan: {autosign}\n"
        f"• Saksi Mingguan: Dikonfigurasi per aktivitas\n\n"
        "Pilih kategori pengaturan di bawah:"
    )

    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(f"🚺 Kondisi: {haid_status}", callback_data="toggle_haid"),
            InlineKeyboardButton(f"🌙 Puasa ({puasa[:8]}...)", callback_data="set_puasa_menu"),
        ],
        [
            InlineKeyboardButton("🕌 Pembiasaan Harian", callback_data="set_daily_menu"),
            InlineKeyboardButton("📆 Pembiasaan Mingguan", callback_data="set_weekly_menu"),
        ],
        [
            InlineKeyboardButton(f"📝 Refleksi ({refleksi})", callback_data="toggle_refleksi"),
            InlineKeyboardButton(f"💼 Status PKL ({internship})", callback_data="toggle_internship"),
        ],
        [
            InlineKeyboardButton(f"✍️ Tanda Tangan ({autosign})", callback_data="toggle_autosign"),
        ],
        [
            InlineKeyboardButton("⬅️ Menu Utama", callback_data="menu_start")
        ]
    ])

    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_chat:
        await update.effective_chat.send_message(text, reply_markup=keyboard)


async def toggle_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    st = get_settings(user_id)

    if query and query.data == "toggle_refleksi":
        new_val = 0 if st.get("refleksi_mingguan") else 1
        update_setting(user_id, "refleksi_mingguan", new_val)
    elif query and query.data == "toggle_internship":
        new_val = 0 if st.get("is_internship") else 1
        update_setting(user_id, "is_internship", new_val)
    elif query and query.data == "toggle_haid":
        new_val = 0 if st.get("is_haid") else 1
        update_setting(user_id, "is_haid", new_val)
    elif query and query.data == "toggle_autosign":
        new_val = 0 if st.get("auto_sign", 1) else 1
        update_setting(user_id, "auto_sign", new_val)

    await settings_menu_handler(update, context)


async def puasa_sunnah_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    text = "🌙 OPSI PUASA SUNNAH:\nPilih preferensi pengisian Puasa Sunnah kamu:"
    options = [
        "Melaksanakan 2 hari",
        "Melaksanakan salah satu hari",
        "Tidak melaksanakan",
        "Tidak ada kegiatan"
    ]

    buttons = [
        [InlineKeyboardButton(opt, callback_data=f"save_puasa_{idx}")]
        for idx, opt in enumerate(options)
    ]
    buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_settings")])

    keyboard = InlineKeyboardMarkup(buttons)
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_chat:
        await update.effective_chat.send_message(text, reply_markup=keyboard)


async def save_puasa_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    options = [
        "Melaksanakan 2 hari",
        "Melaksanakan salah satu hari",
        "Tidak melaksanakan",
        "Tidak ada kegiatan"
    ]

    if query and query.data:
        idx = int(query.data.replace("save_puasa_", ""))
        selected = options[idx] if 0 <= idx < len(options) else options[0]
        update_setting(user_id, "puasa_sunnah", selected)

    await settings_menu_handler(update, context)


DEFAULT_WEEKLY_ACTIVITIES = [
    "Aktivitas Fisik",
    "Sholat Jumat",
    "Membantu Memasak",
    "Membersihkan Rumah",
    "Mencuci Baju",
    "Kuku, Telinga, dan Bercukur"
]


async def weekly_settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    w_settings = get_weekly_activity_settings(user_id)

    lines = ["📆 SAKSI PEMBIASAAN MINGGUAN:\n"]
    buttons = []

    for idx, act in enumerate(DEFAULT_WEEKLY_ACTIVITIES):
        act_data = w_settings.get(act, {})
        w_type = act_data.get("witness_type", "Orang Tua")
        w_name = act_data.get("witness_name", "")
        n_str = f" ({w_name})" if w_name else ""
        lines.append(f"• {act}: Saksi = {w_type}{n_str}")

        buttons.append([
            InlineKeyboardButton(f"⚙️ Saksi {act[:14]}: {w_type}", callback_data=f"edit_w_{idx}")
        ])

    buttons.append([
        InlineKeyboardButton("👥 Set Semua: Orang Tua", callback_data="save_wall_Orang Tua"),
        InlineKeyboardButton("👥 Set Semua: Guru", callback_data="save_wall_Guru"),
    ])
    buttons.append([InlineKeyboardButton("⬅️ Kembali", callback_data="menu_settings")])
    text = "\n".join(lines)

    keyboard = InlineKeyboardMarkup(buttons)
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_chat:
        await update.effective_chat.send_message(text, reply_markup=keyboard)


async def edit_witness_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    raw_data = query.data if query else ""
    # Format: edit_w_{idx} or edit_witness_{act}
    if raw_data.startswith("edit_w_"):
        idx_str = raw_data.replace("edit_w_", "")
        idx = int(idx_str) if idx_str.isdigit() else 0
    else:
        idx = 0

    act_name = DEFAULT_WEEKLY_ACTIVITIES[idx] if 0 <= idx < len(DEFAULT_WEEKLY_ACTIVITIES) else DEFAULT_WEEKLY_ACTIVITIES[0]

    text = (
        f"⚙️ PILIH SAKSI UNTUK: {act_name}\n"
        "Pilih tipe saksi di bawah ini:"
    )

    types = ["Orang Tua", "Guru", "Teman", "Lainnya"]
    buttons = [
        [InlineKeyboardButton(f"👥 Saksi: {t}", callback_data=f"save_w_{idx}_{t}")]
        for t in types
    ]
    buttons.append([InlineKeyboardButton("⬅️ Batal", callback_data="set_weekly_menu")])

    keyboard = InlineKeyboardMarkup(buttons)
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_chat:
        await update.effective_chat.send_message(text, reply_markup=keyboard)


async def save_witness_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    raw_data = query.data if query else ""

    # Expected pattern: save_w_{idx}_{w_type}
    if raw_data.startswith("save_w_"):
        parts = raw_data.split("_", 3)
        if len(parts) >= 4:
            idx = int(parts[2]) if parts[2].isdigit() else 0
            w_type = parts[3]
            act_name = DEFAULT_WEEKLY_ACTIVITIES[idx] if 0 <= idx < len(DEFAULT_WEEKLY_ACTIVITIES) else DEFAULT_WEEKLY_ACTIVITIES[0]

            save_weekly_activity_setting(
                telegram_id=user_id,
                activity_key=act_name,
                activity_name=act_name,
                enabled=1,
                witness_type=w_type,
                witness_name=""
            )

    await weekly_settings_menu_handler(update, context)


async def save_all_witness_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    user_id = update.effective_user.id
    raw_data = query.data if query else ""
    w_type = raw_data.replace("save_wall_", "") if raw_data.startswith("save_wall_") else "Orang Tua"

    for act in DEFAULT_WEEKLY_ACTIVITIES:
        save_weekly_activity_setting(
            telegram_id=user_id,
            activity_key=act,
            activity_name=act,
            enabled=1,
            witness_type=w_type,
            witness_name=""
        )

    await weekly_settings_menu_handler(update, context)


async def daily_settings_menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()

    text = (
        "🕌 PEMBIASAAN HARIAN\n\n"
        "Aktivitas harian dibaca secara dinamis dari Kejar.id saat sinkronisasi.\n"
        "Secara default, semua pembiasaan harian yang tersedia akan diisi dengan status 'Melaksanakan'."
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("⬅️ Kembali", callback_data="menu_settings")]
    ])
    if query:
        await query.edit_message_text(text, reply_markup=keyboard)
    elif update.effective_chat:
        await update.effective_chat.send_message(text, reply_markup=keyboard)

