import sqlite3
import json
from typing import Tuple, List, Dict, Optional, Any
from config import DATABASE_PATH


def get_connection():
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def add_column_if_missing(cursor, table_name, column_name, column_definition):
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = {row["name"] for row in cursor.fetchall()}
    if column_name not in columns:
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}")


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    # 1. Users
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            first_name TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    add_column_if_missing(cursor, "users", "updated_at", "TIMESTAMP")

    # 2. Kejar Accounts (NO password)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS kejar_accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            username TEXT,
            profile_path TEXT,
            connected INTEGER DEFAULT 0,
            connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_sync_at TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    add_column_if_missing(cursor, "kejar_accounts", "username", "TEXT")
    add_column_if_missing(cursor, "kejar_accounts", "connected", "INTEGER DEFAULT 0")
    add_column_if_missing(cursor, "kejar_accounts", "profile_path", "TEXT")
    add_column_if_missing(cursor, "kejar_accounts", "connected_at", "TIMESTAMP")
    add_column_if_missing(cursor, "kejar_accounts", "last_sync_at", "TIMESTAMP")

    # 3. MEB
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meb (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            meb_id TEXT,
            report_period_id TEXT,
            meb_number INTEGER NOT NULL,
            label TEXT,
            start_date TEXT,
            end_date TEXT,
            school_week TEXT,
            school_week_id TEXT,
            status TEXT DEFAULT 'available',
            is_matrikulasi INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
            UNIQUE (telegram_id, meb_number)
        )
    """)
    add_column_if_missing(cursor, "meb", "school_week_id", "TEXT")

    # 4. MEB Target Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS meb_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            start_meb INTEGER DEFAULT 1,
            end_meb INTEGER DEFAULT 5,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    add_column_if_missing(cursor, "meb_settings", "start_meb", "INTEGER DEFAULT 1")
    add_column_if_missing(cursor, "meb_settings", "end_meb", "INTEGER DEFAULT 5")

    # 5. Weekly Activity Settings (per activity witness)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weekly_activity_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            activity_key TEXT NOT NULL,
            activity_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            witness_type TEXT DEFAULT 'Guru',
            witness_name TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
            UNIQUE (telegram_id, activity_key)
        )
    """)

    # 6. Daily Activity Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_activity_settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            activity_key TEXT NOT NULL,
            activity_name TEXT NOT NULL,
            enabled INTEGER DEFAULT 1,
            configuration_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
            UNIQUE (telegram_id, activity_key)
        )
    """)

    # 7. General User Settings
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER UNIQUE NOT NULL,
            puasa_sunnah TEXT DEFAULT 'Melaksanakan 2 hari',
            refleksi_mingguan INTEGER DEFAULT 0,
            is_internship INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
        )
    """)
    add_column_if_missing(cursor, "settings", "puasa_sunnah", "TEXT DEFAULT 'Melaksanakan 2 hari'")
    add_column_if_missing(cursor, "settings", "refleksi_mingguan", "INTEGER DEFAULT 0")
    add_column_if_missing(cursor, "settings", "is_internship", "INTEGER DEFAULT 0")
    add_column_if_missing(cursor, "settings", "is_haid", "INTEGER DEFAULT 0")

    # 8. Action Fill Logs
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS fill_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            meb_number INTEGER,
            activity_date TEXT,
            activity_type TEXT,
            activity_name TEXT,
            action_status TEXT,
            message TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# Helper functions
def create_or_update_user(telegram_id: int, username: str = None, first_name: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO users (telegram_id, username, first_name)
        VALUES (?, ?, ?)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            first_name = excluded.first_name,
            updated_at = CURRENT_TIMESTAMP
    """, (telegram_id, username, first_name))
    conn.commit()
    conn.close()


def set_kejar_account_connected(telegram_id: int, username: str, connected: bool = True, profile_path: str = None):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO kejar_accounts (telegram_id, username, connected, profile_path, connected_at, updated_at)
        VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
        ON CONFLICT(telegram_id) DO UPDATE SET
            username = excluded.username,
            connected = excluded.connected,
            profile_path = COALESCE(excluded.profile_path, kejar_accounts.profile_path),
            updated_at = CURRENT_TIMESTAMP
    """, (telegram_id, username, 1 if connected else 0, profile_path))
    conn.commit()
    conn.close()


def update_last_sync(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE kejar_accounts
        SET last_sync_at = CURRENT_TIMESTAMP
        WHERE telegram_id = ?
    """, (telegram_id,))
    conn.commit()
    conn.close()


def get_kejar_account(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM kejar_accounts WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def is_kejar_connected(telegram_id: int) -> bool:
    acc = get_kejar_account(telegram_id)
    return bool(acc and acc.get("connected") == 1)


def save_user_mebs(telegram_id: int, meb_list: list):
    conn = get_connection()
    cursor = conn.cursor()
    for m in meb_list:
        meb_id = getattr(m, 'id', m.get('id') if isinstance(m, dict) else None)
        report_period_id = getattr(m, 'report_period_id', m.get('report_period_id') if isinstance(m, dict) else None)
        meb_number = getattr(m, 'number', m.get('number') if isinstance(m, dict) else 0)
        label = getattr(m, 'label', m.get('label') if isinstance(m, dict) else '')
        start_date = getattr(m, 'start_date', m.get('start_date') if isinstance(m, dict) else '')
        end_date = getattr(m, 'end_date', m.get('end_date') if isinstance(m, dict) else '')
        school_week = getattr(m, 'school_week', m.get('school_week') if isinstance(m, dict) else '')
        is_matrikulasi = 1 if getattr(m, 'is_matrikulasi', m.get('is_matrikulasi') if isinstance(m, dict) else False) else 0
        school_week_id = getattr(m, 'school_week_id', m.get('school_week_id') if isinstance(m, dict) else meb_id)

        if isinstance(start_date, (str, type(None))):
            s_str = start_date or ''
        else:
            s_str = start_date.isoformat()

        if isinstance(end_date, (str, type(None))):
            e_str = end_date or ''
        else:
            e_str = end_date.isoformat()

        cursor.execute("""
            INSERT INTO meb (
                telegram_id, kejar_id, report_period_id, meb_number, label,
                start_date, end_date, school_week, school_week_id, is_matrikulasi, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(telegram_id, meb_number) DO UPDATE SET
                kejar_id = excluded.kejar_id,
                report_period_id = excluded.report_period_id,
                label = excluded.label,
                start_date = excluded.start_date,
                end_date = excluded.end_date,
                school_week = excluded.school_week,
                school_week_id = excluded.school_week_id,
                is_matrikulasi = excluded.is_matrikulasi,
                updated_at = CURRENT_TIMESTAMP
        """, (telegram_id, meb_id, report_period_id, meb_number, label, s_str, e_str, str(school_week), school_week_id, is_matrikulasi))
    conn.commit()
    conn.close()


def get_user_mebs(telegram_id: int) -> list:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT * FROM meb WHERE telegram_id = ? ORDER BY meb_number ASC
    """, (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save_meb_target(telegram_id: int, start_meb: int, end_meb: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO meb_settings (telegram_id, start_meb, end_meb, updated_at)
        VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(telegram_id) DO UPDATE SET
            start_meb = excluded.start_meb,
            end_meb = excluded.end_meb,
            updated_at = CURRENT_TIMESTAMP
    """, (telegram_id, start_meb, end_meb))
    conn.commit()
    conn.close()


def get_meb_target(telegram_id: int) -> Tuple[int, int]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT start_meb, end_meb FROM meb_settings WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return row["start_meb"], row["end_meb"]
    return 1, 5


def ensure_user_settings(telegram_id: int):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT OR IGNORE INTO settings (telegram_id) VALUES (?)
    """, (telegram_id,))
    cursor.execute("""
        INSERT OR IGNORE INTO meb_settings (telegram_id) VALUES (?)
    """, (telegram_id,))
    conn.commit()
    conn.close()


def get_settings(telegram_id: int) -> dict:
    ensure_user_settings(telegram_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM settings WHERE telegram_id = ?", (telegram_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else {"puasa_sunnah": "Melaksanakan 2 hari", "refleksi_mingguan": 0, "is_internship": 0}


def update_setting(telegram_id: int, field: str, value):
    allowed = {"puasa_sunnah", "refleksi_mingguan", "is_internship", "is_haid"}
    if field not in allowed:
        return
    ensure_user_settings(telegram_id)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        UPDATE settings SET {field} = ?, updated_at = CURRENT_TIMESTAMP WHERE telegram_id = ?
    """, (value, telegram_id))
    conn.commit()
    conn.close()


def save_weekly_activity_setting(telegram_id: int, activity_key: str, activity_name: str, enabled: int = 1, witness_type: str = "Guru", witness_name: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO weekly_activity_settings (telegram_id, activity_key, activity_name, enabled, witness_type, witness_name, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(telegram_id, activity_key) DO UPDATE SET
            activity_name = excluded.activity_name,
            enabled = excluded.enabled,
            witness_type = excluded.witness_type,
            witness_name = excluded.witness_name,
            updated_at = CURRENT_TIMESTAMP
    """, (telegram_id, activity_key, activity_name, enabled, witness_type, witness_name))
    conn.commit()
    conn.close()


def get_weekly_activity_settings(telegram_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM weekly_activity_settings WHERE telegram_id = ?", (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return {r["activity_key"]: dict(r) for r in rows}


def save_daily_activity_setting(telegram_id: int, activity_key: str, activity_name: str, enabled: int = 1, config: dict = None):
    conn = get_connection()
    cursor = conn.cursor()
    cfg_json = json.dumps(config) if config else None
    cursor.execute("""
        INSERT INTO daily_activity_settings (telegram_id, activity_key, activity_name, enabled, configuration_json, updated_at)
        VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(telegram_id, activity_key) DO UPDATE SET
            activity_name = excluded.activity_name,
            enabled = excluded.enabled,
            configuration_json = excluded.configuration_json,
            updated_at = CURRENT_TIMESTAMP
    """, (telegram_id, activity_key, activity_name, enabled, cfg_json))
    conn.commit()
    conn.close()


def get_daily_activity_settings(telegram_id: int) -> dict:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM daily_activity_settings WHERE telegram_id = ?", (telegram_id,))
    rows = cursor.fetchall()
    conn.close()
    return {r["activity_key"]: dict(r) for r in rows}


def log_fill_action(telegram_id: int, meb_number: int, activity_date: str, activity_type: str, activity_name: str, action_status: str, message: str = ""):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO fill_logs (telegram_id, meb_number, activity_date, activity_type, activity_name, action_status, message)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (telegram_id, meb_number, activity_date, activity_type, activity_name, action_status, message))
    conn.commit()
    conn.close()


if __name__ == "__main__":
    init_database()
    print("Database initialized successfully.")