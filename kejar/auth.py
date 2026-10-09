import os

# Load env first so PLAYWRIGHT_BROWSERS_PATH from .env is picked up
from dotenv import load_dotenv
load_dotenv()

# Set Playwright browser path from env (may be overridden by config.py too)
_pw_path = os.environ.get("PLAYWRIGHT_BROWSERS_PATH", "")
if _pw_path:
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _pw_path

import gc
import logging
import re
from typing import Any, Dict

import httpx
from playwright.async_api import async_playwright

from config import KEJAR_BASE_URL
from kejar.browser_session import (
    get_profile_dir,
    save_user_cookies,
    clear_user_cookies,
    ensure_playwright_browsers_async,
)
from kejar.discovery import record_request
from database import set_kejar_account_connected


logger = logging.getLogger("jurnalin.auth")


async def login_kejar_fast_http(
    telegram_id: int,
    username: str,
    password_temp: str,
) -> Dict[str, Any]:
    """
    Try direct HTTP login first.

    Returns success=True only when the login is actually detected as successful.
    If HTTP login fails or requires browser execution, success=False is returned
    so the caller can continue to the Playwright fallback.
    """
    login_url = f"{KEJAR_BASE_URL}/login"
    user_profile = get_profile_dir(telegram_id)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,application/xml;"
            "q=0.9,image/webp,*/*;q=0.8"
        ),
        "Referer": login_url,
    }

    try:
        import urllib.parse

        async with httpx.AsyncClient(
            headers=headers,
            follow_redirects=True,
            timeout=12.0,
        ) as client:
            # Get login page first so we can collect CSRF/session cookies.
            res_get = await client.get(login_url)

            csrf_token = ""
            match = re.search(
                r'name="_token"\s+value="([^"]+)"',
                res_get.text,
            )

            if match:
                csrf_token = match.group(1)

            xsrf_cookie = client.cookies.get("XSRF-TOKEN")
            if xsrf_cookie:
                client.headers["X-XSRF-TOKEN"] = urllib.parse.unquote(
                    xsrf_cookie
                )

            payload = {
                "username": username,
                "identity": username,
                "email": username,
                "password": password_temp,
            }

            if csrf_token:
                payload["_token"] = csrf_token

            res_post = await client.post(
                login_url,
                data=payload,
            )

            cookies_dict = dict(client.cookies)

            cookies_list = [
                {
                    "name": key,
                    "value": value,
                    "domain": ".kejar.id",
                    "path": "/",
                }
                for key, value in cookies_dict.items()
            ]

            url_str = str(res_post.url).lower()

            # Direct HTTP login succeeded.
            if (
                ("/student" in url_str
                 or "/dashboard" in url_str
                 or "home" in url_str)
                and "/login" not in url_str
            ):
                save_user_cookies(
                    telegram_id,
                    cookies_list,
                )

                set_kejar_account_connected(
                    telegram_id,
                    username,
                    True,
                    user_profile,
                )

                logger.info(
                    "Fast HTTP login succeeded for username=%s",
                    username,
                )

                return {
                    "success": True,
                    "captcha": False,
                    "otp": False,
                    "message": "✅ Kejar.id berhasil terhubung.",
                }

            # HTTP login did not prove a successful login.
            # IMPORTANT: return success=False so Playwright can continue.
            logger.info(
                "Fast HTTP login did not succeed for username=%s; "
                "falling back to Playwright.",
                username,
            )

            return {
                "success": False,
                "captcha": False,
                "otp": False,
                "message": "",
            }

    except Exception as ex:
        logger.warning(
            "Fast HTTP login attempt failed: %s",
            ex,
        )

        # Do NOT return a final login error here.
        # The caller must be allowed to try Playwright.
        return {
            "success": False,
            "captcha": False,
            "otp": False,
            "message": "",
        }


async def login_kejar(
    telegram_id: int,
    username: str,
    password_temp: str,
    headless: bool = True,
) -> Dict[str, Any]:
    """
    Login to Kejar.id.

    Flow:
    1. Try direct HTTP login.
    2. If HTTP login does not succeed, fall back to Playwright.
    3. Save cookies/session after successful login.
    """
    # Always ensure a clean slate for new login attempt
    clear_user_cookies(telegram_id)
    user_profile = get_profile_dir(telegram_id)
    login_url = f"{KEJAR_BASE_URL}/login"

    result: Dict[str, Any] = {
        "success": False,
        "captcha": False,
        "otp": False,
        "message": "",
    }

    logger.info(
        "Attempting login for telegram_id=%s, username=%s",
        telegram_id,
        username,
    )

    # ---------------------------------------------------------
    # 1. FAST HTTP LOGIN
    # ---------------------------------------------------------
    fast_res = await login_kejar_fast_http(
        telegram_id,
        username,
        password_temp,
    )

    # Only stop here if HTTP login was actually successful.
    if fast_res.get("success") is True:
        return fast_res

    # Otherwise continue to Playwright.
    logger.info(
        "HTTP login failed or was inconclusive. "
        "Starting Playwright fallback for username=%s",
        username,
    )

    # ---------------------------------------------------------
    # 2. PLAYWRIGHT LOGIN
    # ---------------------------------------------------------
    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--no-zygote",
    ]

    context = None

    try:
        async with async_playwright() as p:

            # First try to launch the browser.
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_profile,
                    headless=headless,
                    args=browser_args,
                )

            except Exception as launch_err:
                logger.warning(
                    "Initial Playwright browser launch failed: %s",
                    launch_err,
                )

                # Try to install the browser once as a fallback.
                try:
                    await ensure_playwright_browsers_async(
                        force=True
                    )

                    context = await p.chromium.launch_persistent_context(
                        user_data_dir=user_profile,
                        headless=headless,
                        args=browser_args,
                    )

                except Exception as install_err:
                    logger.exception(
                        "Unable to start Playwright Chromium."
                    )

                    result["message"] = (
                        "⚠️ Chromium Playwright tidak tersedia di server.\n"
                        f"Detail: {install_err}"
                    )

                    return result

            page = (
                context.pages[0]
                if context.pages
                else await context.new_page()
            )

            # -------------------------------------------------
            # FORCE HTTPS — Kejar.id sometimes redirects http→https
            # which causes ERR_EMPTY_RESPONSE in Playwright
            # -------------------------------------------------
            async def force_https(route, request):
                url = request.url
                if url.startswith("http://app.kejar.id"):
                    new_url = "https://app.kejar.id" + url[len("http://app.kejar.id"):]
                    await route.continue_(url=new_url)
                else:
                    await route.continue_()

            await context.route("http://app.kejar.id/**", force_https)

            # -------------------------------------------------
            # NETWORK DISCOVERY
            # -------------------------------------------------
            async def handle_request(req):
                if "/student/" in req.url:
                    try:
                        post_data = (
                            req.post_data_json
                            if req.post_data
                            else None
                        )

                        record_request(
                            method=req.method,
                            url=req.url,
                            query_params=dict(req.headers),
                            payload=post_data,
                            status_code=200,
                        )

                    except Exception:
                        pass

            page.on("request", handle_request)

            # -------------------------------------------------
            # OPEN LOGIN PAGE
            # -------------------------------------------------
            try:
                await page.goto(
                    login_url,
                    wait_until="domcontentloaded",
                    timeout=15000,
                )

            except Exception as goto_err:
                logger.warning(
                    "Goto timeout/error: %s",
                    goto_err,
                )

            # -------------------------------------------------
            # CHECK EXISTING SESSION (Ensure clean state for target username)
            # -------------------------------------------------
            if (
                "/student" in page.url
                or "/dashboard" in page.url
            ):
                logger.info("Found residual session; clearing context cookies and returning to login page...")
                await context.clear_cookies()
                await page.goto(login_url, wait_until="domcontentloaded", timeout=15000)

            # -------------------------------------------------
            # FIND LOGIN INPUTS
            # -------------------------------------------------
            username_input = page.locator(
                "input[name='username'], "
                "input[type='text'], "
                "input[name='email']"
            ).first

            password_input = page.locator(
                "input[name='password'], "
                "input[type='password']"
            ).first

            try:
                username_visible = await username_input.is_visible(
                    timeout=5000
                )
                password_visible = await password_input.is_visible(
                    timeout=5000
                )
            except Exception:
                username_visible = False
                password_visible = False

            if username_visible and password_visible:
                await username_input.fill(username)
                await password_input.fill(password_temp)

                submit_btn = page.locator(
                    "button[type='submit'], "
                    "input[type='submit']"
                ).first

                try:
                    submit_visible = await submit_btn.is_visible(
                        timeout=3000
                    )
                except Exception:
                    submit_visible = False

                if submit_visible:
                    await submit_btn.click()
                else:
                    await password_input.press("Enter")

                await page.wait_for_timeout(3000)

            else:
                logger.warning(
                    "Login form fields were not found or not visible."
                )

            # -------------------------------------------------
            # CAPTCHA CHECK
            # -------------------------------------------------
            captcha_frame = page.locator(
                "iframe[src*='recaptcha'], "
                "iframe[src*='hcaptcha'], "
                "iframe[src*='turnstile']"
            )

            page_content = (await page.content()).lower()

            if (
                await captcha_frame.count() > 0
                or "captcha" in page_content
            ):
                result["captcha"] = True
                result["message"] = (
                    "⚠️ Kejar.id meminta CAPTCHA.\n"
                    "Silakan selesaikan CAPTCHA di browser yang "
                    "digunakan oleh server.\n"
                    "Setelah selesai, tekan Sinkron MEB."
                )

                await context.close()
                context = None

                return result

            # -------------------------------------------------
            # OTP CHECK
            # -------------------------------------------------
            if (
                "otp" in page_content
                or "verifikasi" in page_content
            ):
                result["otp"] = True
                result["message"] = (
                    "⚠️ Kejar.id meminta kode OTP.\n"
                    "Silakan masukkan kode OTP sesuai proses "
                    "verifikasi akun.\n"
                    "Setelah selesai, tekan Sinkron MEB."
                )

                await context.close()
                context = None

                return result

            # -------------------------------------------------
            # WAIT FOR LOGIN REDIRECT
            # -------------------------------------------------
            try:
                await page.wait_for_url(
                    lambda url: "/login" not in url,
                    timeout=8000,
                )
            except Exception:
                pass

            # -------------------------------------------------
            # SAVE SESSION COOKIES
            # -------------------------------------------------
            cookies = await context.cookies()

            save_user_cookies(
                telegram_id,
                cookies,
            )

            # More reliable success check.
            current_url = page.url.lower()

            logged_in = (
                "/login" not in current_url
                or any(
                    cookie.get("name")
                    in (
                        "session",
                        "remember_web",
                        "XSRF-TOKEN",
                    )
                    for cookie in cookies
                )
            )

            if logged_in:
                set_kejar_account_connected(
                    telegram_id,
                    username,
                    True,
                    user_profile,
                )

                result["success"] = True
                result["message"] = (
                    "✅ Kejar.id berhasil terhubung."
                )

            else:
                set_kejar_account_connected(
                    telegram_id,
                    username,
                    False,
                    user_profile,
                )

                result["message"] = (
                    "❌ Login gagal. "
                    "Periksa username dan password kamu."
                )

            await context.close()
            context = None

    except Exception as e:
        logger.exception(
            "Login error for telegram_id=%s",
            telegram_id,
        )

        result["message"] = (
            "⚠️ Terjadi kesalahan saat login: "
            f"{str(e)}"
        )

    finally:
        # Make sure browser context is closed if an unexpected
        # exception occurred before the normal close.
        if context is not None:
            try:
                await context.close()
            except Exception:
                pass

        # Clear password reference from memory.
        try:
            del password_temp
        except Exception:
            pass

        gc.collect()

    return result
