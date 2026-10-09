"""
Login ulang dan intercept XHR endpoints dari Kejar.id.
Jalankan setelah bot berhasil login untuk verify endpoints.

Usage: python diagnose_deep.py
"""
import asyncio
import json
import getpass
from playwright.async_api import async_playwright, Route
from kejar.browser_session import get_profile_dir, save_user_cookies, clear_user_cookies
from database import set_kejar_account_connected
from config import KEJAR_BASE_URL

import sqlite3
conn = sqlite3.connect('jurnalin.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT telegram_id, username FROM kejar_accounts LIMIT 5')
rows = [dict(r) for r in cur.fetchall()]
conn.close()

print('Akun di database:')
for i, r in enumerate(rows):
    print(f'  {i+1}. tid={r["telegram_id"]}, user={r["username"]}')

if not rows:
    print('Tidak ada akun. Run bot dulu.')
    exit(1)

tid = rows[0]['telegram_id']
username = input(f'\nUsername Kejar.id [{rows[0]["username"]}]: ').strip() or rows[0]['username']
password = getpass.getpass('Password Kejar.id: ')
profile_dir = get_profile_dir(tid)

# Clear old session
clear_user_cookies(tid)

captured_xhr = {}

async def run():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--no-sandbox", "--disable-gpu"],
        )

        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Force HTTPS redirects
        async def force_https(route: Route, request):
            url = request.url
            if url.startswith('http://app.kejar.id'):
                await route.continue_(url='https://app.kejar.id' + url[len('http://app.kejar.id'):])
            else:
                await route.continue_()
        await ctx.route('http://app.kejar.id/**', force_https)

        # Capture XHR after login
        async def on_response(resp):
            url = resp.url
            if '/student/' not in url:
                return
            if resp.request.resource_type not in ('xhr', 'fetch'):
                return
            try:
                ct = resp.headers.get('content-type', '')
                if 'json' not in ct:
                    return
                body = await resp.json()
                base = url.split('?')[0]
                query = url.split('?')[1] if '?' in url else ''
                print(f'\n✅ {resp.request.method} {base}')
                if query:
                    print(f'   params: {query[:100]}')
                if isinstance(body, dict):
                    print(f'   keys: {list(body.keys())[:10]}')
                    captured_xhr[base] = {
                        'method': resp.request.method,
                        'sample_url': url,
                        'body_preview': json.dumps(body)[:400],
                    }
                    for k in ['current_school_week', 'previous_school_week', 'school_weeks', 'data', 'habits']:
                        if k in body:
                            print(f'   [{k}] = {json.dumps(body[k])[:250]}')
                elif isinstance(body, list):
                    print(f'   list[{len(body)}] first: {json.dumps(body[0] if body else {})[:200]}')
                    captured_xhr[base] = {
                        'method': resp.request.method,
                        'sample_url': url,
                        'body_preview': json.dumps(body[:2])[:300],
                    }
            except Exception:
                pass

        page.on('response', on_response)

        # Step 1: Login
        print(f'\nNavigating to login page...')
        try:
            await page.goto(f'{KEJAR_BASE_URL}/login', wait_until='domcontentloaded', timeout=15000)
        except Exception as e:
            print(f'goto error: {e}')

        await page.wait_for_timeout(1000)
        print(f'Login page URL: {page.url}')

        # Fill login form
        try:
            await page.locator('input[name="username"], input[type="text"], input[name="email"]').first.fill(username)
            await page.locator('input[name="password"], input[type="password"]').first.fill(password)
            await page.locator('button[type="submit"], input[type="submit"]').first.click()
            print('Form submitted, waiting...')
        except Exception as e:
            print(f'Form error: {e}')

        await page.wait_for_timeout(4000)
        print(f'After login URL: {page.url}')

        if '/login' in page.url.lower():
            print('❌ Masih di halaman login. Cek username/password.')
            await ctx.close()
            return

        print('✅ Login berhasil!')

        # Step 2: Navigate to journal page and capture XHR
        print('\nNavigating to journal-weekly...')
        try:
            await page.goto(
                f'{KEJAR_BASE_URL}/student/journal-weekly',
                wait_until='networkidle',
                timeout=20000,
            )
        except Exception as e:
            print(f'Nav warning: {e}')

        print(f'Journal URL: {page.url}')
        await page.wait_for_timeout(5000)

        # Save cookies
        cookies = await ctx.cookies()
        save_user_cookies(tid, cookies)
        set_kejar_account_connected(tid, username, True, profile_dir)
        print(f'✅ Saved {len(cookies)} cookies & updated DB')

        await ctx.close()

    print(f'\n{"="*60}')
    print(f'Captured {len(captured_xhr)} unique XHR endpoints:')
    for base, info in captured_xhr.items():
        print(f'\n  {info["method"]} {base}')
        print(f'  Sample: {info["sample_url"][:100]}')
        print(f'  Response: {info["body_preview"][:200]}')

asyncio.run(run())
