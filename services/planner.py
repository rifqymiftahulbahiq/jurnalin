from datetime import date
from typing import Dict, List, Any
from database import (
    get_meb_target,
    get_user_mebs,
    get_settings,
    get_weekly_activity_settings,
    get_daily_activity_settings
)
from kejar.meb import MebPeriod, parse_kejar_date, eligible_dates


def generate_journal_plan(telegram_id: int, today: date = None) -> Dict[str, Any]:
    """
    Generates a dry-run execution plan for filling MEBs.
    """
    if today is None:
        today = date.today()

    start_meb, end_meb = get_meb_target(telegram_id)
    user_mebs = get_user_mebs(telegram_id)
    user_settings = get_settings(telegram_id)
    weekly_settings = get_weekly_activity_settings(telegram_id)
    daily_settings = get_daily_activity_settings(telegram_id)

    target_mebs = [m for m in user_mebs if start_meb <= m["meb_number"] <= end_meb]

    plan = {
        "telegram_id": telegram_id,
        "target_range": f"MEB {start_meb} → MEB {end_meb}",
        "total_mebs": len(target_mebs),
        "mebs_detail": [],
        "total_eligible_days": 0,
        "total_planned_actions": 0,
        "puasa_sunnah": user_settings.get("puasa_sunnah", "Melaksanakan 2 hari"),
        "refleksi_mingguan": user_settings.get("refleksi_mingguan", 0),
        "is_internship": user_settings.get("is_internship", 0),
        "behavior_journal": "🚫 Tidak disentuh (sesuai aturan keamanan & integritas)."
    }

    for m in target_mebs:
        s_date = parse_kejar_date(m["start_date"])
        e_date = parse_kejar_date(m["end_date"])

        if not s_date or not e_date:
            continue

        meb_obj = MebPeriod(
            id=m.get("kejar_id", ""),
            report_period_id=m.get("report_period_id", ""),
            number=m["meb_number"],
            label=m.get("label", f"MEB {m['meb_number']}"),
            start_date=s_date,
            end_date=e_date,
            school_week=m.get("school_week", ""),
            is_matrikulasi=bool(m.get("is_matrikulasi", 0)),
            school_week_id=m.get("school_week_id", m.get("kejar_id", ""))
        )

        dates = eligible_dates(meb_obj, today)
        plan["total_eligible_days"] += len(dates)

        meb_plan = {
            "meb_number": m["meb_number"],
            "label": meb_obj.label,
            "start_date": s_date.isoformat(),
            "end_date": e_date.isoformat(),
            "school_week_id": meb_obj.school_week_id,
            "eligible_dates": [d.isoformat() for d in dates],
            "daily_actions": [],
            "weekly_actions": []
        }

        # Planned daily actions per eligible date
        for d in dates:
            # Default daily habits (Salat, Zikir, Grooming, etc.)
            meb_plan["daily_actions"].append({
                "date": d.isoformat(),
                "action": "UPDATE_DAILY_HABITS",
                "status": "READY_UPDATE"
            })
            plan["total_planned_actions"] += 1

        # Planned weekly actions (per eligible date or week end)
        if dates:
            meb_plan["weekly_actions"].append({
                "action": "UPDATE_WEEKLY_HABITS",
                "status": "READY_UPDATE",
                "witness_configured": len(weekly_settings) > 0
            })
            plan["total_planned_actions"] += 1

        plan["mebs_detail"].append(meb_plan)

    return plan
