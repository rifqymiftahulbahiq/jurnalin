from datetime import date
from typing import Dict, List, Any, Optional
from kejar.client import KejarClient, SessionExpiredError
import logging

logger = logging.getLogger("jurnalin.daily")

# These are tried in order — first one that succeeds is used
DAILY_ACTIVITIES_ENDPOINTS = [
    "/student/journal-daily/activities",
    "/student/journal_salat_zikir/activities",
    "/student/journal-weekly/habituation",  # fallback: some versions serve daily via this
]

DAILY_BULK_UPDATE_ENDPOINTS = [
    "/student/journal-daily/bulk-update",
    "/student/journal_salat_zikir/bulk-update",
]

# Cache which endpoints work (keyed by telegram_id to handle per-user API versions)
_working_get_endpoint: Dict[int, str] = {}
_working_patch_endpoint: Dict[int, str] = {}


async def get_daily_activities(client: KejarClient, activity_date: date, calendar_id: str) -> Dict[str, Any]:
    """
    Fetches daily activity list. Tries multiple endpoint variants automatically.
    """
    tid = client.telegram_id

    # Use cached working endpoint if available
    if tid in _working_get_endpoint:
        try:
            return await client.get(
                _working_get_endpoint[tid],
                params={"date": activity_date.isoformat(), "calendarId": calendar_id}
            )
        except SessionExpiredError:
            raise
        except Exception:
            # Cached endpoint may have stopped working, clear cache and retry all
            del _working_get_endpoint[tid]

    last_error = None
    for ep in DAILY_ACTIVITIES_ENDPOINTS:
        try:
            result = await client.get(
                ep,
                params={"date": activity_date.isoformat(), "calendarId": calendar_id}
            )
            _working_get_endpoint[tid] = ep
            logger.debug(f"Daily activities endpoint: {ep}")
            return result
        except SessionExpiredError:
            raise
        except Exception as e:
            last_error = e
            logger.debug(f"Daily endpoint {ep} failed: {e}")
            continue

    raise last_error or Exception("No working daily activities endpoint found")


async def update_daily_deed(
    client: KejarClient,
    activity_date: date,
    calendar_id: str,
    categories_payload: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """
    Sends bulk update for daily habits. Tries multiple endpoint variants.
    """
    tid = client.telegram_id

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

    if tid in _working_patch_endpoint:
        try:
            return await client.patch(_working_patch_endpoint[tid], data=payload, params=params)
        except SessionExpiredError:
            raise
        except Exception:
            del _working_patch_endpoint[tid]

    last_error = None
    for ep in DAILY_BULK_UPDATE_ENDPOINTS:
        try:
            result = await client.patch(ep, data=payload, params=params)
            _working_patch_endpoint[tid] = ep
            logger.debug(f"Daily bulk-update endpoint: {ep}")
            return result
        except SessionExpiredError:
            raise
        except Exception as e:
            last_error = e
            logger.debug(f"Daily patch endpoint {ep} failed: {e}")
            continue

    raise last_error or Exception("No working daily bulk-update endpoint found")


def parse_daily_response(response: dict) -> List[Dict[str, Any]]:
    """
    Parses dynamic daily activities response.
    Handles multiple response envelope formats from Kejar.id API.
    """
    result = []

    # Unwrap various possible envelope formats
    data = response.get("data", response)

    if isinstance(data, dict):
        items = (
            data.get("items")
            or data.get("activities")
            or data.get("habits")
            or data.get("categories")
            or []
        )
    elif isinstance(data, list):
        items = data
    else:
        items = []

    # Last resort: check top-level keys
    if not items:
        items = (
            response.get("items")
            or response.get("activities")
            or response.get("habits")
            or response.get("categories")
            or []
        )

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
