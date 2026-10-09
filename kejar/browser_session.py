import os
import json
import sys
import subprocess
import asyncio
import logging
import shutil
from typing import Dict, List, Any
from config import PROFILES_DIR

logger = logging.getLogger("jurnalin.browser")


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
    profile_dir = get_profile_dir(telegram_id)
    if os.path.exists(profile_dir):
        try:
            shutil.rmtree(profile_dir)
        except Exception:
            for item in os.listdir(profile_dir):
                item_path = os.path.join(profile_dir, item)
                try:
                    if os.path.isdir(item_path):
                        shutil.rmtree(item_path)
                    else:
                        os.remove(item_path)
                except Exception:
                    pass
    os.makedirs(profile_dir, exist_ok=True)


def _run_playwright_install():
    """Install Playwright browser (chromium). Works on both Linux and Windows."""
    try:
        logger.info("Installing Playwright chromium browser...")
        result = subprocess.run(
            [sys.executable, "-m", "playwright", "install", "chromium"],
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode == 0:
            logger.info("Playwright chromium installed successfully.")
            return True
        else:
            logger.error(f"playwright install failed: {result.stderr[:300]}")
            # Try installing deps on Linux
            if sys.platform.startswith("linux"):
                logger.info("Trying to install system dependencies...")
                subprocess.run(
                    [sys.executable, "-m", "playwright", "install-deps", "chromium"],
                    capture_output=True,
                    timeout=120,
                )
                # Retry install
                result2 = subprocess.run(
                    [sys.executable, "-m", "playwright", "install", "chromium"],
                    capture_output=True,
                    text=True,
                    timeout=300,
                )
                return result2.returncode == 0
            return False
    except Exception as ex:
        logger.error(f"Failed to install Playwright browser: {ex}")
        return False


_browsers_installed = False


async def ensure_playwright_browsers_async(force: bool = False):
    global _browsers_installed
    if _browsers_installed and not force:
        return
    ok = await asyncio.to_thread(_run_playwright_install)
    if ok:
        _browsers_installed = True


def ensure_playwright_browsers(force: bool = False):
    global _browsers_installed
    if _browsers_installed and not force:
        return
    ok = _run_playwright_install()
    if ok:
        _browsers_installed = True
