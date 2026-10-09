"""
find_endpoints.py — Login dan intercept semua XHR calls dari Kejar.id.

Usage:
    python find_endpoints.py <username> <password>

Contoh:
    python find_endpoints.py rifqymift518 passwordkamu

Script ini akan:
1. Login ke Kejar.id pakai Playwright (browser)
2. Navigate ke halaman journal
3. Capture semua XHR/fetch API calls yang dibuat browser
4. Simpan hasilnya ke endpoints_found.json
"""
import asyncio
import json
import sys
from playwright.async_api import async_playwright, Route
from kejar.browser_session import get_profile_dir, save_user_cookies, clear_user_cookies
from database import set_kejar_account_connected
from config import KEJAR_BASE_URL

if len(sys.argv) < 3:
    print('Usage: python find_endpoints.py <username> <password>')
    sys.exit(1)

import sqlite3
conn = sqlite3.connect('jurnalin.db')
conn.row_factory = sqlite3.Row
cur = conn.cursor()
cur.execute('SELECT telegram_id FROM kejar_accounts LIMIT 1')
row = cur.fetchone()
conn.close()

if not row:
    print('Tidak ada user di DB. Run bot dulu dan login sekali.')
    sys.exit(1)

tid = row['telegram_id']
username = sys.argv[1]
password = sys.argv[2]
profile_dir = get_profile_dir(tid)
clear_user_cookies(tid)

captured = {}

async def run():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--no-sandbox"],
        )
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()

        # Force HTTPS
        async def force_https(route: Route, req):
            url = req.url
            if url.startswith('http://app.kejar.id'):
                await route.continue_(url='https://app.kejar.id' + url[len('http://app.kejar.id'):])
            else:
                await route.continue_()
        await ctx.route('http://app.kejar.id/**', force_https)

        # Capture ALL responses from /student/ endpoints
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
                query = url[len(base)+1:] if '?' in url else ''
                print(f'\n✅ {resp.request.method} {base}')
                if query:
                    print(f'   params: {query[:100]}')
                print(f'   status: {resp.status}')
                if isinstance(body, dict):
                    print(f'   keys: {list(body.keys())[:12]}')
                    print(f'   preview: {json.dumps(body)[:300]}')
                elif isinstance(body, list):
                    print(f'   list[{len(body)}]: {json.dumps(body[:1])[:200]}')
                captured[base] = {
                    'method': resp.request.method,
                    'sample_url': url,
                    'status': resp.status,
                    'body': body,
                }
            except Exception:
                pass

        page.on('response', on_response)

        # Login
        print('Opening login page...')
        await page.goto(f'{KEJAR_BASE_URL}/login', wait_until='domcontentloaded', timeout=20000)
        await page.wait_for_timeout(1000)

        try:
            await page.locator('input[name="username"], input[type="text"]').first.fill(username)
            await page.locator('input[name="password"], input[type="password"]').first.fill(password)
            await page.locator('button[type="submit"]').first.click()
        except Exception as e:
            print(f'Form error: {e}')

        print('Waiting after login...')
        await page.wait_for_timeout(5000)
        print(f'URL: {page.url}')

        if '/login' in page.url.lower():
            print('❌ Login gagal. Cek username/password.')
            await ctx.close()
            return

        print('✅ Login OK! Navigating to journal pages...')

        # Navigate to journal-weekly to trigger XHR calls
        for nav_url in [
            f'{KEJAR_BASE_URL}/student/journal-weekly',
        ]:
            print(f'\nNavigating to: {nav_url}')
            try:
                await page.goto(nav_url, wait_until='networkidle', timeout=20000)
            except Exception as e:
                print(f'  nav warning: {e}')
            await page.wait_for_timeout(3000)
            print(f'  Current URL: {page.url}')

        # Save cookies
        cookies = await ctx.cookies()
        save_user_cookies(tid, cookies)
        set_kejar_account_connected(tid, username, True, profile_dir)
        print(f'\n✅ Saved {len(cookies)} cookies')

        await ctx.close()

    # Save results
    with open('endpoints_found.json', 'w') as f:
        json.dump({k: {
            'method': v['method'],
            'sample_url': v['sample_url'],
            'status': v['status'],
            'body_preview': json.dumps(v.get('body', {}))[:500],
        } for k, v in captured.items()}, f, indent=2)

    print(f'\n{"="*60}')
    print(f'Found {len(captured)} endpoints. Saved to endpoints_found.json')

asyncio.run(run())
