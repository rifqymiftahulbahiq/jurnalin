from datetime import date
from typing import Dict, Any, List
import logging
from kejar.client import KejarClient, SessionExpiredError
from kejar.meb import parse_meb_response
from database import save_user_mebs, update_last_sync, set_kejar_account_connected
from kejar.browser_session import get_profile_dir

logger = logging.getLogger("jurnalin.sync")


async def sync_kejar_data(telegram_id: int) -> Dict[str, Any]:
    """
    Syncs school week / MEB data and available activities from Kejar.id to SQLite database.
    """
    client = KejarClient(telegram_id)
    result = {
        "success": False,
        "message": "",
        "mebs_synced": 0,
        "meb_list": []
    }

    try:
        endpoints = [
            "/student/school-weeks",
            "/student/dashboard",
            "/student/journal_salat_zikir/activities"
        ]

        meb_data = None
        mebs = []

        for ep in endpoints:
            try:
                res = await client.get(ep)
                if res:
                    parsed = parse_meb_response(res)
                    if parsed:
                        mebs = parsed
                        meb_data = res
                        break
            except Exception as e:
                logger.debug(f"Endpoint {ep} failed: {e}")
                continue

        if mebs:
            save_user_mebs(telegram_id, mebs)
            update_last_sync(telegram_id)
            result["success"] = True
            result["mebs_synced"] = len(mebs)
            result["meb_list"] = mebs
            labels = ", ".join([f"{m.label} ({m.start_date.strftime('%d/%m')}-{m.end_date.strftime('%d/%m')})" for m in mebs])
            result["message"] = f"✅ Sinkronisasi berhasil! Ditemukan {len(mebs)} MEB:\n{labels}"
        else:
            update_last_sync(telegram_id)
            result["success"] = True
            result["message"] = "✅ Sesi terhubung. Tekan [🔄 Sinkron MEB] untuk memperbarui data MEB terbaru dari Kejar.id."

    except SessionExpiredError:
        set_kejar_account_connected(telegram_id, "", False)
        result["message"] = "🔐 Sesi Kejar.id sudah berakhir. Silakan login kembali."
    except Exception as e:
        logger.error(f"Sync error for telegram_id={telegram_id}: {e}")
        result["message"] = f"⚠️ Kejar.id tidak merespons atau error: {str(e)}"
    finally:
        await client.close()

    return result
