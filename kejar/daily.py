from datetime import date
from typing import Dict, List, Any, Optional
from kejar.client import KejarClient

DAILY_BULK_UPDATE_ENDPOINT = "/student/journal_salat_zikir/bulk-update"
DAILY_ACTIVITIES_ENDPOINT = "/student/journal_salat_zikir/activities"


async def get_daily_activities(client: KejarClient, activity_date: date, calendar_id: str) -> Dict[str, Any]:
    return await client.get(
        DAILY_ACTIVITIES_ENDPOINT,
        params={
            "date": activity_date.isoformat(),
            "calendarId": calendar_id,
        }
    )


def parse_daily_response(response: dict) -> List[Dict[str, Any]]:
    """
    Parses dynamic daily activities response without hardcoding habit items.
    """
    result = []
    items = response.get("data", [])
    if isinstance(items, dict):
        items = items.get("items", [])

    for item in items:
        if not isinstance(item, dict):
            continue
        result.append({
            "key": item.get("key", item.get("name", "")),
            "name": item.get("name", item.get("habit", "")),
            "category": item.get("category", ""),
            "deedable_id": item.get("deedable_id", item.get("id")),
            "deed": item.get("deed"),
            "deed_id": item.get("deed", {}).get("id") if isinstance(item.get("deed"), dict) else None,
            "options": item.get("options", []),
            "point_categories": item.get("point_categories", item.get("details", [])),
            "raw": item
        })

    return result


async def update_daily_deed(
    client: KejarClient,
    activity_date: date,
    calendar_id: str,
    categories_payload: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Sends bulk update for daily habits.
    """
    params = {
        "weekStartDate": activity_date.isoformat(),
        "weekEndDate": activity_date.isoformat(),
        "calendarId": calendar_id,
    }

    payload = {
        "payloadHabit[date]": activity_date.isoformat(),
    }

    for idx, cat in enumerate(categories_payload):
        prefix = f"payloadHabit[categories][{idx}]"
        payload[f"{prefix}[category]"] = str(cat.get("category", ""))
        payload[f"{prefix}[point]"] = str(cat.get("point", 1))
        payload[f"{prefix}[do]"] = str(cat.get("do", "true")).lower()
        payload[f"{prefix}[deedable_id]"] = str(cat.get("deedable_id", ""))
        if cat.get("deed_id"):
            payload[f"{prefix}[deed_id]"] = str(cat["deed_id"])

    return await client.patch(DAILY_BULK_UPDATE_ENDPOINT, data=payload)
