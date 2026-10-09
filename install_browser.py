"""
Install Playwright browser untuk Jurnalin Bot.
Jalankan ini satu kali di server sebelum menjalankan bot.

Usage:
    python install_browser.py
"""
import sys
import subprocess

print("Installing Playwright chromium browser...")

# Step 1: Install browser binary
r = subprocess.run(
    [sys.executable, "-m", "playwright", "install", "chromium"],
    timeout=300,
)
if r.returncode != 0:
    print("Browser install failed, trying with system deps first...")
    # Linux: install system dependencies first
    subprocess.run(
        [sys.executable, "-m", "playwright", "install-deps", "chromium"],
        timeout=120,
    )
    r = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "chromium"],
        timeout=300,
    )

if r.returncode == 0:
    print("\n✅ Playwright chromium browser berhasil diinstall!")
    print("Sekarang kamu bisa menjalankan bot dengan: python bot.py")
else:
    print("\n❌ Install gagal.")
    print("Coba jalankan manual:")
    print("  python -m playwright install chromium")
    print("  python -m playwright install-deps chromium  # Linux only")
    sys.exit(1)
