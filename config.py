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

# Ensure Playwright browser binary path is stored inside the application workspace
PLAYWRIGHT_BROWSERS_PATH = os.getenv("PLAYWRIGHT_BROWSERS_PATH", str(BASE_DIR / ".ms-playwright"))
os.environ["PLAYWRIGHT_BROWSERS_PATH"] = PLAYWRIGHT_BROWSERS_PATH

# Create directories if they don't exist
os.makedirs(PROFILES_DIR, exist_ok=True)
os.makedirs(PLAYWRIGHT_BROWSERS_PATH, exist_ok=True)

