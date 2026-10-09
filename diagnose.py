"""
Jurnalin Diagnostic Tool
========================
Jalankan ini untuk cek status koneksi ke Kejar.id.

Usage:
    python diagnose.py
"""
import asyncio
import sqlite3
import httpx
from kejar.browser_session import get_user_cookies_dict
from config import KEJAR_BASE_URL


def get_all_users():
    conn = sqlite3.connect('jurnalin.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT telegram_id, username, connected, last_sync_at FROM kejar_accounts')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def get_mebs(tid):
    conn = sqlite3.connect('jurnalin.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute('SELECT meb_number, meb_id, school_week_id, start_date, end_date, completion_status FROM meb WHERE telegram_id=? ORDER BY meb_number LIMIT 5', (tid,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


async def check_session(tid, username):
    cookies = get_user_cookies_dict(tid)
    print(f'\n{"="*60}')
    print(f'User: {username} (tid={tid})')
    print(f'Cookies: {list(cookies.keys())}')

    if not cookies:
        print('❌ Tidak ada cookies. Perlu login ulang via bot.')
        return False

    headers = {
        'Accept': 'text/html',
        'User-Agent': 'Mozilla/5.0 Chrome/130.0.0.0 Safari/537.36',
    }

    try:
        async with httpx.AsyncClient(
            base_url=KEJAR_BASE_URL,
            headers=headers,
            cookies=cookies,
            timeout=10.0,
            follow_redirects=False,
        ) as client:
            r = await client.get('/student')
            loc = r.headers.get('location', '-')
            print(f'Session check: HTTP {r.status_code}, Location: {loc[:60]}')

            if r.status_code == 302:
                if 'login' in loc.lower():
                    print('❌ SESI EXPIRED — Harus login ulang via bot!')
                    return False
                else:
                    print(f'✅ Sesi aktif (redirect ke: {loc[:60]})')
                    return True
            elif r.status_code == 200:
                print('✅ Sesi aktif')
                return True
            else:
                print(f'⚠️ Status tidak biasa: {r.status_code}')
                return False
    except Exception as e:
        print(f'Error: {e}')
        return False


async def main():
    users = get_all_users()
    if not users:
        print('Tidak ada user di database.')
        return

    print(f'Users di database: {len(users)}')
    for u in users:
        valid = await check_session(u['telegram_id'], u['username'])

        mebs = get_mebs(u['telegram_id'])
        print(f'\nMEBs di DB: {len(mebs)} (showing first 5)')
        for m in mebs:
            meb_id = m.get('meb_id') or ''
            sw_id = m.get('school_week_id') or ''
            is_fallback = meb_id.startswith('sw_auto_') or sw_id.startswith('sw_auto_')
            flag = '⚠️ ESTIMASI' if is_fallback else '✅ REAL'
            print(f'  MEB {m["meb_number"]}: {flag} | meb_id={meb_id} | sw_id={sw_id} | start={m["start_date"]}')

        if not valid:
            print(f'\n👉 LANGKAH PERBAIKAN:')
            print(f'   1. Buka Telegram bot kamu')
            print(f'   2. Kirim /start')
            print(f'   3. Pilih menu 🔐 Login / Akun → Hubungkan Ulang')
            print(f'   4. Masukkan username dan password Kejar.id')
            print(f'   5. Setelah login berhasil, tekan 🔄 Sinkron MEB')
            print(f'   6. Cek lagi dengan: python diagnose.py')
        else:
            print(f'\n✅ Sesi valid. Kalau sync MEB masih gagal, jalankan:')
            print(f'   python diagnose_deep.py')

asyncio.run(main())
