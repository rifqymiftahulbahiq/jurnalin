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

# Create profiles directory if it doesn't exist
os.makedirs(PROFILES_DIR, exist_ok=True)
