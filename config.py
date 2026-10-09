import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env file
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "jurnalin.db"))
PROFILES_DIR = os.getenv("PROFILES_DIR", str(BASE_DIR / "kejar_profiles"))

KEJAR_BASE_URL = os.getenv("KEJAR_BASE_URL", "https://app.kejar.id")

# Playwright browser path — only set if explicitly configured in .env
# If not set, Playwright uses its default location per platform:
#   Linux:   ~/.cache/ms-playwright
#   Windows: %LOCALAPPDATA%\ms-playwright
#   macOS:   ~/Library/Caches/ms-playwright
_pw_path = os.getenv("PLAYWRIGHT_BROWSERS_PATH", "")
if _pw_path:
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = _pw_path

# Ensure necessary directories exist
os.makedirs(PROFILES_DIR, exist_ok=True)

