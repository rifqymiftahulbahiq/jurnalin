from datetime import date
from typing import Dict, List, Any, Tuple
from database import is_kejar_connected, get_user_mebs, get_meb_target
from kejar.meb import MebPeriod, eligible_dates


def validate_user_connection(telegram_id: int) -> Tuple[bool, str]:
    if not is_kejar_connected(telegram_id):
        return False, "🔐 Sesi login tidak terhubung. Silakan hubungkan akun Kejar.id kamu terlebih dahulu."
    return True, "OK"


def validate_target_range(start_meb: int, end_meb: int) -> Tuple[bool, str]:
    if not (1 <= start_meb <= 36) or not (1 <= end_meb <= 36):
        return False, "⚠️ Target MEB harus berada dalam rentang MEB 1 sampai MEB 36."
    if start_meb > end_meb:
        return False, "⚠️ MEB awal tidak boleh lebih besar dari MEB akhir."
    return True, "OK"


def validate_available_mebs(telegram_id: int) -> Tuple[bool, List[dict], str]:
    start_meb, end_meb = get_meb_target(telegram_id)
    all_mebs = get_user_mebs(telegram_id)
    if not all_mebs:
        return False, [], "⚠️ Data MEB belum tersinkron. Silakan tekan [🔄 Sinkron MEB] terlebih dahulu."

    matched = [m for m in all_mebs if start_meb <= m["meb_number"] <= end_meb]
    if not matched:
        return False, [], f"⚠️ MEB {start_meb} → MEB {end_meb} belum tersedia di akun Kejar.id kamu."

    return True, matched, "OK"
