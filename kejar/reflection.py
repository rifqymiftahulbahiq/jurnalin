from typing import Dict, Any, Optional


def process_reflection(reflection_enabled: bool, user_text: Optional[str] = None) -> Dict[str, Any]:
    """
    Weekly Reflection processing.
    Skipped if OFF or if user has provided no text.
    """
    if not reflection_enabled:
        return {
            "status": "SKIPPED",
            "message": "Refleksi Mingguan dinonaktifkan dalam Pengaturan."
        }

    if not user_text:
        return {
            "status": "SKIPPED",
            "message": "Belum ada input refleksi mingguan dari pengguna."
        }

    return {
        "status": "READY",
        "text": user_text
    }
