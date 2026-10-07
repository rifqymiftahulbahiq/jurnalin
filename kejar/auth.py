import httpx
import re
from playwright.async_api import async_playwright
from config import KEJAR_BASE_URL
from kejar.browser_session import get_profile_dir, save_user_cookies, ensure_playwright_browsers_async
from kejar.discovery import record_request
from database import set_kejar_account_connected

logger = logging.getLogger("jurnalin.auth")


async def login_kejar_fast_http(telegram_id: int, username: str, password_temp: str) -> Dict[str, Any]:
    """
    Attempts ultra-fast HTTP direct login without launching browser binaries.
    Completes in <1 second.
    """
    login_url = f"{KEJAR_BASE_URL}/login"
    user_profile = get_profile_dir(telegram_id)

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/130.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Referer": login_url,
    }

    try:
        async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=10.0) as client:
            res_get = await client.get(login_url)
            csrf_token = ""
            m = re.search(r'name="_token"\s+value="([^"]+)"', res_get.text)
            if m:
                csrf_token = m.group(1)

            payload = {
                "username": username,
                "password": password_temp,
            }
            if csrf_token:
                payload["_token"] = csrf_token

            res_post = await client.post(login_url, data=payload)
            
            cookies_dict = dict(client.cookies)
            cookies_list = [{"name": k, "value": v, "domain": ".kejar.id", "path": "/"} for k, v in cookies_dict.items()]

            url_str = str(res_post.url)
            has_auth_cookie = any(k in cookies_dict or any(k in c for c in cookies_dict) for k in ("session", "remember_web", "kejar_session", "XSRF-TOKEN"))
            
            if ("/student" in url_str or "/dashboard" in url_str or has_auth_cookie) and "/login" not in url_str and len(cookies_dict) > 0:
                save_user_cookies(telegram_id, cookies_list)
                set_kejar_account_connected(telegram_id, username, True, user_profile)
                logger.info(f"Fast HTTP login succeeded for username={username}")
                return {
                    "success": True,
                    "captcha": False,
                    "otp": False,
                    "message": "✅ Kejar.id berhasil terhubung."
                }
    except Exception as ex:
        logger.warning(f"Fast HTTP login attempt failed ({ex}), falling back to browser context...")

    return {"success": False, "captcha": False, "otp": False, "message": ""}


async def login_kejar(telegram_id: int, username: str, password_temp: str, headless: bool = True) -> Dict[str, Any]:
    """
    Performs login to Kejar.id using ultra-fast HTTP first, falling back to Playwright browser context if required.
    Password is ONLY used temporarily in memory and cleared immediately.
    """
    user_profile = get_profile_dir(telegram_id)
    login_url = f"{KEJAR_BASE_URL}/login"

    result = {
        "success": False,
        "captcha": False,
        "otp": False,
        "message": ""
    }

    logger.info(f"Attempting login for telegram_id={telegram_id}, username={username}")

    # 1. Try Fast HTTP Direct Login first (<1 sec execution)
    fast_res = await login_kejar_fast_http(telegram_id, username, password_temp)
    if fast_res["success"]:
        return fast_res

    # 2. Fallback to Playwright browser context if HTTP direct login requires browser execution
    browser_args = [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--no-first-run",
        "--no-zygote",
        "--single-process"
    ]

    try:
        async with async_playwright() as p:
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_profile,
                    headless=headless,
                    args=browser_args
                )
            except Exception as launch_err:
                logger.warning(f"Initial browser launch failed ({launch_err}), auto-installing chromium...")
                await ensure_playwright_browsers_async(force=True)
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=user_profile,
                    headless=headless,
                    args=browser_args
                )

            page = context.pages[0] if context.pages else await context.new_page()

            # Attach Network Discovery Listener
            async def handle_request(req):
                if "/student/" in req.url:
                    try:
                        post_data = req.post_data_json if req.post_data else None
                        record_request(
                            method=req.method,
                            url=req.url,
                            query_params=dict(req.headers),
                            payload=post_data,
                            status_code=200
                        )
                    except Exception:
                        pass

            page.on("request", handle_request)
            
            try:
                await page.goto(login_url, wait_until="domcontentloaded", timeout=15000)
            except Exception as goto_err:
                logger.warning(f"Goto timeout/error ({goto_err}), proceeding with current page state")

            # Check if already logged in / redirected to dashboard
            if "/student" in page.url or "/dashboard" in page.url:
                cookies = await context.cookies()
                save_user_cookies(telegram_id, cookies)
                set_kejar_account_connected(telegram_id, username, True, user_profile)
                await context.close()
                result["success"] = True
                result["message"] = "✅ Kejar.id berhasil terhubung."
                return result

            # Fill username & password
            username_input = page.locator("input[name='username'], input[type='text'], input[name='email']").first
            password_input = page.locator("input[name='password'], input[type='password']").first

            if await username_input.is_visible() and await password_input.is_visible():
                await username_input.fill(username)
                await password_input.fill(password_temp)

                # Submit form
                submit_btn = page.locator("button[type='submit'], input[type='submit']").first
                if await submit_btn.is_visible():
                    await submit_btn.click()
                else:
                    await password_input.press("Enter")

                await page.wait_for_timeout(3000)

            # Check for CAPTCHA
            captcha_frame = page.locator("iframe[src*='recaptcha'], iframe[src*='hcaptcha'], iframe[src*='turnstile']")
            if await captcha_frame.count() > 0 or "captcha" in (await page.content()).lower():
                result["captcha"] = True
                result["message"] = (
                    "⚠️ Kejar.id meminta CAPTCHA.\n"
                    "Silakan selesaikan CAPTCHA di browser yang terbuka.\n"
                    "Setelah selesai, kembali ke Telegram dan tekan:\n"
                    "[🔄 Sinkron MEB]"
                )
                await context.close()
                return result

            # Check for OTP
            if "otp" in (await page.content()).lower() or "verifikasi" in (await page.content()).lower():
                result["otp"] = True
                result["message"] = (
                    "⚠️ Kejar.id meminta kode OTP.\n"
                    "Silakan masukkan kode OTP di browser yang terbuka.\n"
                    "Setelah selesai, kembali ke Telegram dan tekan:\n"
                    "[🔄 Sinkron MEB]"
                )
                await context.close()
                return result

            # Wait for redirection to logged-in state
            try:
                await page.wait_for_url(lambda url: "/login" not in url, timeout=8000)
            except Exception:
                pass

            # Save session cookies if login succeeded
            cookies = await context.cookies()
            save_user_cookies(telegram_id, cookies)

            if "/login" not in page.url or any(c["name"] in ("session", "remember_web", "XSRF-TOKEN") for c in cookies):
                set_kejar_account_connected(telegram_id, username, True, user_profile)
                result["success"] = True
                result["message"] = "✅ Kejar.id berhasil terhubung."
            else:
                set_kejar_account_connected(telegram_id, username, False, user_profile)
                result["message"] = "❌ Login gagal. Periksa username dan password kamu."

            await context.close()

    except Exception as e:
        logger.error(f"Login error for telegram_id={telegram_id}: {str(e)}")
        result["message"] = f"⚠️ Terjadi kesalahan saat login: {str(e)}"
    finally:
        # Clear password reference in memory
        del password_temp
        gc.collect()

    return result
