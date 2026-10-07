import logging
from typing import Dict, Any, Optional
from playwright.async_api import async_playwright
from config import KEJAR_BASE_URL
from kejar.browser_session import get_profile_dir, save_user_cookies, ensure_playwright_browsers
from kejar.client import KejarClient

logger = logging.getLogger("jurnalin.signature")

SIGNATURE_ENDPOINT = "/student/journal-weekly/signature"


async def sign_weekly_journal_api(client: KejarClient, calendar_id: str) -> Dict[str, Any]:
    """
    Attempts to submit journal signature via API POST request.
    """
    try:
        data = {
            "calendarId": calendar_id,
            "school_week_id": calendar_id,
        }
        res = await client.post(SIGNATURE_ENDPOINT, data=data)
        logger.info(f"Signed journal via API for calendarId={calendar_id}")
        return {"success": True, "message": "✅ Jurnal berhasil ditandatangani."}
    except Exception as e:
        logger.warning(f"API signature failed, falling back to browser: {e}")
        return {"success": False, "message": str(e)}


async def sign_weekly_journal_browser(telegram_id: int, username: str, password_temp: Optional[str] = None, calendar_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Automates clicking the 'Tanda Tangani' and 'Simpan' button in Kejar.id via Playwright browser session.
    """
    user_profile = get_profile_dir(telegram_id)
    url = f"{KEJAR_BASE_URL}/student/journal-weekly"

    result = {"success": False, "message": ""}

    try:
        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_profile,
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
            except Exception as launch_err:
                logger.warning(f"Signature browser launch failed ({launch_err}), auto-installing chromium...")
                ensure_playwright_browsers(force=True)
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_profile,
                    headless=True,
                    args=["--no-sandbox", "--disable-setuid-sandbox"]
                )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.goto(url, wait_until="networkidle", timeout=30000)

            # Look for 'Tanda Tangani' button
            sign_btn = page.locator("button:has-text('Tanda Tangani'), a:has-text('Tanda Tangani'), div:has-text('Tanda Tangani')").first
            if await sign_btn.is_visible():
                await sign_btn.click()
                await page.wait_for_timeout(1500)

                # Look for 'Simpan' button in modal
                simpan_btn = page.locator("button:has-text('Simpan'), input[value='Simpan']").first
                if await simpan_btn.is_visible():
                    # If password field is present in signature modal
                    pass_input = page.locator("input[type='password']").first
                    if password_temp and await pass_input.is_visible():
                        await pass_input.fill(password_temp)

                    await simpan_btn.click()
                    await page.wait_for_timeout(2000)

                    cookies = await context.cookies()
                    save_user_cookies(telegram_id, cookies)
                    result["success"] = True
                    result["message"] = "✍️ Jurnal berhasil ditandatangani otomatis!"
                else:
                    result["message"] = "⚠️ Tombol Simpan tanda tangan tidak ditemukan."
            else:
                result["success"] = True
                result["message"] = "ℹ️ Jurnal sudah ditandatangani atau tombol tidak tersedia."

            await context.close()

    except Exception as e:
        logger.error(f"Browser signature error: {e}")
        result["message"] = f"⚠️ Gagal melakukan tanda tangan: {str(e)}"

    return result
