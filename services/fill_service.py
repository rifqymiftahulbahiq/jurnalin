from datetime import date
from typing import Dict, Any, List
import logging
from kejar.client import KejarClient, SessionExpiredError
from kejar.weekly import get_weekly_habits, flatten_weekly_habits, update_weekly_deed, get_existing_deed
from kejar.daily import get_daily_activities, parse_daily_response, update_daily_deed
from kejar.signature import sign_weekly_journal_api
from kejar.behavior import get_behavior_journal_status
from services.planner import generate_journal_plan
from database import get_settings, get_weekly_activity_settings, log_fill_action

logger = logging.getLogger("jurnalin.fill")


class FillService:
    def __init__(self, telegram_id: int, mode: str = "DRY_RUN"):
        self.telegram_id = telegram_id
        self.mode = mode.upper()  # "DRY_RUN" or "REAL"

    async def execute_fill(self, today: date = None) -> Dict[str, Any]:
        if today is None:
            today = date.today()

        plan = generate_journal_plan(self.telegram_id, today)

        summary = {
            "mode": self.mode,
            "target_range": plan["target_range"],
            "success_count": 0,
            "skipped_count": 0,
            "failed_count": 0,
            "details": [],
            "behavior_journal": plan["behavior_journal"],
            "unvalidated_create_warning": False
        }

        if self.mode == "DRY_RUN":
            # DRY RUN MODE: Simulate actions without calling API mutators
            for meb in plan["mebs_detail"]:
                for d_str in meb["eligible_dates"]:
                    summary["success_count"] += 1
                    summary["details"].append({
                        "meb": meb["meb_number"],
                        "date": d_str,
                        "activity": "Pembiasaan Harian",
                        "status": "SUCCESS (DRY_RUN)",
                        "message": "Simulasi update pembiasaan harian berhasil."
                    })

                if meb["eligible_dates"]:
                    summary["success_count"] += 1
                    summary["details"].append({
                        "meb": meb["meb_number"],
                        "date": meb["eligible_dates"][-1],
                        "activity": "Pembiasaan Mingguan",
                        "status": "SUCCESS (DRY_RUN)",
                        "message": "Simulasi update pembiasaan mingguan dengan saksi berhasil."
                    })

            # Non-routine & Behavior summary in Dry Run
            summary["skipped_count"] += 1
            summary["details"].append({
                "meb": "-",
                "date": "-",
                "activity": "Jurnal Perilaku",
                "status": "SKIPPED",
                "message": "🚫 Jurnal Perilaku tidak disentuh."
            })
            return summary

        # REAL MODE: Perform actual network updates using KejarClient
        client = KejarClient(self.telegram_id)
        user_settings = get_settings(self.telegram_id)
        weekly_settings = get_weekly_activity_settings(self.telegram_id)
        is_internship = bool(user_settings.get("is_internship", 0))
        is_haid = bool(user_settings.get("is_haid", 0))
        is_female = (user_settings.get("gender") == "Perempuan") or is_haid

        try:
            for meb in plan["mebs_detail"]:
                meb_num = meb["meb_number"]
                calendar_id = meb["school_week_id"]

                # 1. Fill Weekly Habits if dates are eligible
                if meb["eligible_dates"]:
                    s_date = date.fromisoformat(meb["start_date"])
                    e_date = date.fromisoformat(meb["end_date"])
                    try:
                        resp = await get_weekly_habits(client, s_date, e_date, calendar_id)
                        habits = flatten_weekly_habits(resp, is_internship=is_internship)

                        for h in habits:
                            h_id = h["id"]
                            h_name = h["habit"]
                            details = h.get("details", [])
                            if not details:
                                continue

                            # Get saksi per activity setting
                            act_set = weekly_settings.get(h_name, {})
                            if act_set.get("enabled") == 0:
                                continue

                            # Exclude Sholat Jumat for female students
                            if "sholat jumat" in h_name.lower() and is_female:
                                continue

                            # Choose best category
                            best_detail = details[0]
                            cat_name = best_detail.get("category", "Melaksanakan")
                            point = best_detail.get("point", 1)

                            w_type = act_set.get("witness_type", "Orang Tua")
                            w_name = act_set.get("witness_name", "")

                            for d_str in meb["eligible_dates"]:
                                existing_deed = get_existing_deed(h, d_str)
                                deed_id = existing_deed.get("id") if existing_deed else None
                                action_type = "UPDATE" if deed_id else "CREATE"

                                try:
                                    await update_weekly_deed(
                                        client,
                                        habit_id=h_id,
                                        category=cat_name,
                                        point=point,
                                        activity_date=d_str,
                                        witness_type=w_type,
                                        witness_name=w_name,
                                        deed_id=deed_id
                                    )
                                    summary["success_count"] += 1
                                    summary["details"].append({
                                        "meb": meb_num,
                                        "date": d_str,
                                        "activity": f"Weekly: {h_name}",
                                        "status": "SUCCESS",
                                        "message": f"{action_type} deed berhasil (Saksi: {w_type})"
                                    })
                                    log_fill_action(self.telegram_id, meb_num, d_str, "WEEKLY", h_name, "SUCCESS", f"{action_type} deed_id={deed_id}")
                                except Exception as ex:
                                    summary["failed_count"] += 1
                                    summary["details"].append({
                                        "meb": meb_num,
                                        "date": d_str,
                                        "activity": f"Weekly: {h_name}",
                                        "status": "FAILED",
                                        "message": str(ex)
                                    })
                                    log_fill_action(self.telegram_id, meb_num, d_str, "WEEKLY", h_name, "FAILED", str(ex))

                    except Exception as e:
                        logger.error(f"Weekly habits fill error for MEB {meb_num}: {e}")

                # 2. Fill Daily Habits
                for d_str in meb["eligible_dates"]:
                    d_date = date.fromisoformat(d_str)
                    try:
                        raw_daily = await get_daily_activities(client, d_date, calendar_id)
                        daily_items = parse_daily_response(raw_daily)

                        cat_payloads = []
                        for item in daily_items:
                            deed_id = item.get("deed_id")
                            deedable_id = item.get("deedable_id")
                            item_name = item.get("name", "").lower()
                            if deedable_id:
                                # Determine category based on haid status for salat/zikir
                                selected_cat = "Melaksanakan"
                                do_flag = "true"
                                if is_haid and any(s in item_name for s in ("salat", "sholat", "zikir")):
                                    opts = item.get("options", [])
                                    if "Saya sedang berhalangan" in opts:
                                        selected_cat = "Saya sedang berhalangan"
                                    elif "Halangan" in opts:
                                        selected_cat = "Halangan"
                                    else:
                                        selected_cat = "Tidak melaksanakan"
                                    do_flag = "false"

                                cat_entry = {
                                    "category": selected_cat,
                                    "point": 0 if is_haid and any(s in item_name for s in ("salat", "sholat")) else 1,
                                    "do": do_flag,
                                    "deedable_id": deedable_id
                                }
                                if deed_id:
                                    cat_entry["deed_id"] = deed_id
                                cat_payloads.append(cat_entry)

                        if cat_payloads:
                            await update_daily_deed(client, d_date, calendar_id, cat_payloads)
                            summary["success_count"] += 1
                            summary["details"].append({
                                "meb": meb_num,
                                "date": d_str,
                                "activity": "Pembiasaan Harian",
                                "status": "SUCCESS",
                                "message": f"Bulk update/create {len(cat_payloads)} aktivitas harian berhasil."
                            })
                            log_fill_action(self.telegram_id, meb_num, d_str, "DAILY", "Bulk Daily", "SUCCESS", f"{len(cat_payloads)} items")
                        else:
                            summary["skipped_count"] += 1
                            summary["details"].append({
                                "meb": meb_num,
                                "date": d_str,
                                "activity": "Pembiasaan Harian",
                                "status": "SKIPPED",
                                "message": "Tidak ada item harian yang dapat diproses."
                            })
                            log_fill_action(self.telegram_id, meb_num, d_str, "DAILY", "Bulk Daily", "SKIPPED", "CREATE request belum tervalidasi")

                    except Exception as ex:
                        logger.error(f"Daily habit error for date {d_str}: {ex}")
                        summary["failed_count"] += 1
                        summary["details"].append({
                            "meb": meb_num,
                            "date": d_str,
                            "activity": "Pembiasaan Harian",
                            "status": "FAILED",
                            "message": str(ex)
                        })
                        log_fill_action(self.telegram_id, meb_num, d_str, "DAILY", "Bulk Daily", "FAILED", str(ex))

                # 3. Auto-sign completed MEB if auto_sign setting is enabled
                if user_settings.get("auto_sign", 1) == 1 and meb["eligible_dates"]:
                    try:
                        sign_res = await sign_weekly_journal_api(client, calendar_id)
                        if sign_res.get("success"):
                            summary["details"].append({
                                "meb": meb_num,
                                "date": "-",
                                "activity": "Tanda Tangan",
                                "status": "SUCCESS",
                                "message": "✍️ Jurnal berhasil ditandatangani."
                            })
                    except Exception as e_sign:
                        logger.debug(f"Signature step exception: {e_sign}")

        except SessionExpiredError:
            summary["failed_count"] += 1
            summary["details"].append({
                "meb": "-",
                "date": "-",
                "activity": "Auth",
                "status": "FAILED",
                "message": "🔐 Sesi Kejar.id sudah berakhir. Silakan login kembali."
            })
        finally:
            await client.close()

        return summary
