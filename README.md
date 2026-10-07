# 🤖 JURNALIN - Telegram Bot Assistant untuk Kejar.id

**Jurnalin** adalah asisten Telegram pintar yang membantu siswa mengelola dan mengisi jurnal MEB / Pembiasaan pada platform Kejar.id secara efisien, terstruktur, dan aman.

---

## 🚀 Fitur Utama

- **🔐 Multi-User Session Terisolasi**: Setiap pengguna Telegram memiliki folder profil browser Playwright sendiri (`kejar_profiles/<telegram_id>/`). Sesi antar pengguna terpisah total.
- **🛡️ Kerahasiaan Credentials**: Password HANYA digunakan sementara di memori untuk login Playwright lokal. Password **TIDAK PERNAH** disimpan ke SQLite, file `.env`, file log, atau dikirim ke API pihak ketiga. Pesan Telegram yang berisi password langsung dihapus otomatis.
- **🛡️ Penanganan CAPTCHA & OTP**: Mengikuti aturan keamanan resmi, bot tidak melakukan bypass CAPTCHA/OTP secara ilegal. Pengguna dapat menyelesaikan CAPTCHA/OTP di browser Playwright secara manual jika diminta.
- **🎯 Dynamic MEB Discovery & Range MEB 1–36**: Membaca data *school_week* aktual dari Kejar.id. Target MEB dapat dikonfigurasi dari MEB 1 hingga MEB 36.
- **📆 Date Eligibility Guard**: Hanya mengizinkan pengisian untuk tanggal yang sudah berlalu atau hari ini (`start_date <= date <= min(end_date, today)`). Tanggal masa depan pada minggu berjalan tidak akan diisi secara prematur.
- **🕌 Pembiasaan Harian & Mingguan Dinamis**: Membaca struktur kategori, deedable_id, dan deed_id secara fleksibel langsung dari API Kejar.id tanpa mengandalkan daftar hardcoded.
- **👥 Saksi Mingguan per Aktivitas**: Konfigurasi saksi (Guru, Teman, Orang Tua, Lainnya) dapat diatur per aktivitas mingguan secara spesifik.
- **💼 Support Status Internship / PKL**: Mendukung atribut `show_for_internship`. Aktivitas yang tidak berlaku saat PKL akan dilewati secara otomatis jika opsi PKL diaktifkan.
- **🌙 Configurable Puasa Sunnah**: Menyediakan 4 opsi preferensi (Melaksanakan 2 hari, 1 hari, Tidak melaksanakan, Tidak ada kegiatan).
- **👀 Dry-Run Mode & Preview**: Simulasi pengisian jurnal (Dry-Run) sebelum melakukan penulisan aktual.
- **⚠️ Konfirmasi Sebelum Write**: Pengisian aktual hanya berjalan setelah ada konfirmasi manual dari pengguna.
- **🚫 Perlindungan Jurnal Perilaku**: Bot **TIDAK PERNAH** menyentuh atau mengisi Jurnal Perilaku/Karakter demi menjaga integritas data siswa.

---

## 📁 Struktur Project

```
jurnalin-bot/
│
├── bot.py                      # Main entry point & Telegram handlers registration
├── config.py                   # Environment & directory path configuration
├── database.py                 # SQLite database initialization & migrations
├── requirements.txt            # Python dependencies
├── .env                        # Environment variables (bot token)
├── .env.example                # Template configuration file
├── README.md                   # Complete documentation & usage guide
│
├── kejar/                      # Kejar.id integration package
│   ├── __init__.py
│   ├── client.py               # Async HTTP client with user session cookies
│   ├── browser_session.py     # Playwright user profile session manager
│   ├── auth.py                 # Playwright automated login & CAPTCHA/OTP handler
│   ├── meb.py                  # MEB period parser & date eligibility calculator
│   ├── daily.py                # Dynamic daily activities parser & update generator
│   ├── weekly.py               # Dynamic weekly habituation parser & update generator
│   ├── non_routine.py          # Non-routine activities handler
│   ├── reflection.py           # Optional weekly reflection handler
│   ├── behavior.py             # Behavior journal safety module (🚫 Untouched)
│   ├── discovery.py            # Safe network request discovery recorder
│   └── parser.py               # Unified data parsing helper
│
├── handlers/                   # Telegram bot UI handlers
│   ├── __init__.py
│   ├── start.py                # Start command, main menu & natural language parser
│   ├── login.py                # Login conversation handler & password redactor
│   ├── meb.py                  # Target MEB selector & MEB list viewer
│   ├── settings.py             # User settings (Daily, Weekly, Saksi, Puasa, PKL)
│   ├── preview.py              # Dry-run preview handler
│   └── journal.py              # Confirmation dialog & real fill execution handler
│
├── services/                   # Business logic services
│   ├── __init__.py
│   ├── sync_service.py         # Syncs MEBs & activities from Kejar.id
│   ├── planner.py              # Dry-run action planner
│   ├── fill_service.py         # Write engine (Dry-run & Real mode)
│   └── validation.py           # Request & range validator
│
├── tests/                      # Automated unit test suite
│   ├── __init__.py
│   ├── fixtures/               # Test fixtures (JSON responses)
│   │   ├── meb_response.json
│   │   ├── weekly_habituation.json
│   │   └── daily_response.json
│   ├── test_meb.py
│   ├── test_weekly.py
│   ├── test_daily.py
│   └── test_planner.py
│
└── kejar_profiles/             # Isolated Playwright user browser profiles
    └── <telegram_id>/
```

---

## 🛠️ Cara Instalasi

1. **Clone / Buka repository**:
   ```bash
   cd C:\RIFQY\jurnalin-bot
   ```

2. **Gunakan Python Virtual Environment**:
   ```bash
   .venv\Scripts\activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install -r requirements.txt
   playwright install chromium
   ```

4. **Konfigurasi Environment**:
   Salin `.env.example` ke `.env` dan masukkan token bot Telegram dari `@BotFather`:
   ```env
   TELEGRAM_BOT_TOKEN=8277606124:AAHLmU_EzJbg36laQsGTw4cLT5fkOObJefo
   ```

---

## ⚙️ Cara Menjalankan Bot

Jalankan perintah berikut di terminal:
```bash
python bot.py
```

---

## 🧪 Menjalankan Unit Tests

Jalankan pengujian otomatis (menggunakan mock fixture tanpa menyentuh akun Kejar.id asli):
```bash
pytest
```

---

## 📖 Panduan Penggunaan Bot

### 1. Memulai Bot
Buka Telegram dan cari bot kamu, lalu kirim `/start` atau tekan tombol **Start**.

### 2. Menghubungkan Akun Kejar.id
1. Tekan tombol `🔐 Hubungkan Kejar.id`.
2. Masukkan **Username / NIS / Email** Kejar.id kamu.
3. Masukkan **Password** Kejar.id kamu.
4. Bot akan menghapus pesan password secara otomatis dari chat Telegram demi keamanan.
5. Bot membuka browser session terisolasi dan melakukan login ke Kejar.id.

### 3. Memilih Target MEB
- **Via Menu**: Tekan `🎯 Target MEB`, lalu pilih MEB Awal dan MEB Akhir (MEB 1 s/d MEB 36).
- **Via Natural Language**: Ketik langsung di pesan Telegram:
  `Isi MEB 1 sampai MEB 5` atau `MEB 10 - MEB 12`.

### 4. Melakukan Preview & Pengisian Jurnal
1. Tekan `👀 Preview Isi` untuk melihat pratinjau tanggal eligible dan rencana tindakan.
2. Tekan `✍️ Isi Jurnal`.
3. Tekan `[✅ Ya, Isi Jurnal Sekarang]` untuk menyetujui pengisian.
4. Bot akan memproses pengisian jurnal dan menampilkan ringkasan laporan (Success, Skipped, Failed).

---

## 📊 Status Fitur Project

| Fitur | Status | Keterangan |
| :--- | :---: | :--- |
| Core Bot Infrastructure & Database | **READY** | SQLite, environment config, & handlers lengkap. |
| Multi-User Session Isolation | **READY** | Folder profil Chromium terpisah per Telegram User ID. |
| Secure Credential Handling | **READY** | Password tidak pernah disimpan/dilog, pesan password otomatis dihapus. |
| Kejar.id Authentication | **READY** | Playwright persistent login, CAPTCHA/OTP warning trigger. |
| MEB Synchronization & Dynamic Dates | **READY** | Membaca actual `school_week` & menghitung `eligible_dates`. |
| Target MEB Selector (1–36) | **READY** | Dukungan menu & natural language text parsing. |
| Dynamic Daily & Weekly Habituation | **READY** | Response parser dynamic tanpa hardcoded UUID/kategori. |
| Per-Activity Witness Configuration | **READY** | Saksi (Guru, Teman, Orang Tua, Lainnya) disimpan per aktivitas. |
| Internship / PKL Support | **READY** | Memperhatikan atribut `show_for_internship`. |
| Behavior Journal Safety | **READY** | 🚫 Jurnal Perilaku dijamin tidak pernah disentuh bot. |
| Dry-Run Mode & Confirmation | **READY** | Simulasi preview & konfirmasi eksplisit sebelum write. |
| Existing Deed UPDATE Request | **READY** | PATCH `/student/journal_salat_zikir/bulk-update` & `/student/journal-weekly/deed-habbit`. |
| Automatic CREATE Request | **READY** | Mengirimkan `deedable_id` / `habit_id` untuk pembuatan deed baru secara otomatis. |

