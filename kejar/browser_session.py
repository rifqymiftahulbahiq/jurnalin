import os
import json
from typing import Dict, List, Any
from config import PROFILES_DIR


def get_profile_dir(telegram_id: int) -> str:
    path = os.path.join(PROFILES_DIR, str(telegram_id))
    os.makedirs(path, exist_ok=True)
    return path


def get_cookies_file(telegram_id: int) -> str:
    return os.path.join(get_profile_dir(telegram_id), "cookies.json")


def save_user_cookies(telegram_id: int, cookies: List[Dict[str, Any]]):
    file_path = get_cookies_file(telegram_id)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, indent=2)


def get_user_cookies_dict(telegram_id: int) -> Dict[str, str]:
    file_path = get_cookies_file(telegram_id)
    if not os.path.exists(file_path):
        return {}
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            cookies_list = json.load(f)
            cookie_dict = {}
            for c in cookies_list:
                if isinstance(c, dict) and "name" in c and "value" in c:
                    cookie_dict[c["name"]] = c["value"]
            return cookie_dict
    except Exception:
        return {}


def has_saved_session(telegram_id: int) -> bool:
    cookies = get_user_cookies_dict(telegram_id)
    return len(cookies) > 0


def clear_user_cookies(telegram_id: int):
    file_path = get_cookies_file(telegram_id)
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except Exception:
            pass


_browsers_installed = False

async def ensure_playwright_browsers_async(force: bool = False):
    global _browsers_installed
    if _browsers_installed and not force:
        return
    try:
        import sys
        import subprocess
        import asyncio
        import logging
        logger = logging.getLogger("jurnalin.browser")
        logger.info("Verifying Playwright chromium and headless-shell installation...")
        await asyncio.to_thread(subprocess.run, [sys.executable, "-m", "playwright", "install", "chromium", "chromium-headless-shell"], check=True)
        _browsers_installed = True
        logger.info("Playwright browser verification complete.")
    except Exception as ex:
        import logging
        logging.getLogger("jurnalin.browser").error(f"Failed to install Playwright browser: {ex}")


def ensure_playwright_browsers(force: bool = False):
    global _browsers_installed
    if _browsers_installed and not force:
        return
    try:
        import sys
        import subprocess
        import logging
        logger = logging.getLogger("jurnalin.browser")
        logger.info("Verifying Playwright chromium and headless-shell installation...")
        subprocess.run([sys.executable, "-m", "playwright", "install", "chromium", "chromium-headless-shell"], check=True)
        _browsers_installed = True
        logger.info("Playwright browser verification complete.")
    except Exception as ex:
        import logging
        logging.getLogger("jurnalin.browser").error(f"Failed to install Playwright browser: {ex}")



