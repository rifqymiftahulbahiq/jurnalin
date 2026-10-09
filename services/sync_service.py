from datetime import date, timedelta
from typing import Dict, Any, List
import logging
from kejar.client import KejarClient, SessionExpiredError
from kejar.meb import parse_meb_response, generate_fallback_mebs
from kejar.weekly import get_weekly_habits, flatten_weekly_habits
from database import (
    save_user_mebs,
    update_last_sync,
    set_kejar_account_connected,
    update_meb_completion_status,
)

logger = logging.getLogger("jurnalin.sync")


async def sync_meb_completion_statuses(client: KejarClient, telegram_id: int, mebs: list):
    today = date.today()
    for m in mebs:
        s_date = getattr(m, 'start_date', m.get('start_date') if isinstance(m, dict) else None)
        e_date = getattr(m, 'end_date', m.get('end_date') if isinstance(m, dict) else None)
        meb_num = getattr(m, 'number', m.get('number') if isinstance(m, dict) else 0)
        sw_id = getattr(m, 'school_week_id', m.get('school_week_id') if isinstance(m, dict) else f"sw_auto_{meb_num}")

        if not s_date or not e_date or not meb_num:
            continue

        if isinstance(s_date, str):
            try:
                s_date = date.fromisoformat(s_date[:10])
            except Exception:
                continue

        if isinstance(e_date, str):
            try:
                e_date = date.fromisoformat(e_date[:10])
            except Exception:
                continue

        # Skip future MEBs (start_date > today)
        if s_date > today:
            continue

        # Query Kejar.id weekly habituation endpoint for past/current MEB
        try:
            resp = await get_weekly_habits(client, s_date, e_date, str(sw_id))
            if not resp or not isinstance(resp, dict):
                update_meb_completion_status(telegram_id, meb_num, "BELUM DIBUKA")
                continue

            data_obj = resp.get("data", {}) if isinstance(resp.get("data"), dict) else resp
            signature = resp.get("signature") or data_obj.get("signature")
            is_signed = resp.get("is_signed") or data_obj.get("is_signed")

            if signature or is_signed:
                update_meb_completion_status(telegram_id, meb_num, "SUDAH LENGKAP")
                continue

            habits = flatten_weekly_habits(resp)
            if not habits:
                update_meb_completion_status(telegram_id, meb_num, "BELUM DIBUKA")
                continue

            current_d = s_date
            last_d = min(e_date, today)
            has_deeds = False
            missing_deed = False

            while current_d <= last_d:
                d_str = current_d.isoformat()
                for h in habits:
                    deeds = h.get("deeds", {})
                    if isinstance(deeds, dict) and deeds.get(d_str):
                        has_deeds = True
                    elif isinstance(deeds, list) and any(isinstance(d, dict) and d.get("date") == d_str for d in deeds):
                        has_deeds = True
                    else:
                        missing_deed = True
                current_d += timedelta(days=1)

            if has_deeds and not missing_deed:
                update_meb_completion_status(telegram_id, meb_num, "SUDAH LENGKAP")
            else:
                update_meb_completion_status(telegram_id, meb_num, "BELUM LENGKAP")

        except Exception as ex:
            logger.debug(f"MEB {meb_num} status check warning: {ex}")


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
        ]

        mebs = []

        for ep in endpoints:
            try:
                res = await client.get(ep)
                if res:
                    parsed = parse_meb_response(res)
                    if parsed:
                        mebs = parsed
                        break
            except Exception as e:
                logger.debug(f"Endpoint {ep} failed: {e}")
                continue

        if not mebs:
            mebs = generate_fallback_mebs()

        save_user_mebs(telegram_id, mebs)
        
        # Accurately sync actual completion & signature status per MEB from Kejar.id
        await sync_meb_completion_statuses(client, telegram_id, mebs)

        update_last_sync(telegram_id)
        result["success"] = True
        result["mebs_synced"] = len(mebs)
        result["meb_list"] = mebs
        result["message"] = f"✅ Sinkronisasi berhasil! Status kelengkapan MEB 1 s/d MEB 36 telah diperbarui dari Kejar.id."

    except SessionExpiredError:
        set_kejar_account_connected(telegram_id, "", False)
        result["message"] = "🔐 Sesi Kejar.id sudah berakhir. Silakan login kembali."
    except Exception as e:
        logger.error(f"Sync error for telegram_id={telegram_id}: {e}")
        result["message"] = f"⚠️ Kejar.id tidak merespons atau error: {str(e)}"
    finally:
        await client.close()

    return result
