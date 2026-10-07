from datetime import date
from typing import Dict, List, Any, Optional
from kejar.client import KejarClient

HABITUATION_ENDPOINT = "/student/journal-weekly/habituation"
UPDATE_WEEKLY_ENDPOINT = "/student/journal-weekly/deed-habbit"


async def get_weekly_habits(
    client: KejarClient,
    start_date: date,
    end_date: date,
    calendar_id: str,
) -> Dict[str, Any]:
    return await client.get(
        HABITUATION_ENDPOINT,
        params={
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "subtype": "HABIT",
            "calendarId": calendar_id,
        },
    )


def flatten_weekly_habits(response: dict, is_internship: bool = False) -> List[Dict[str, Any]]:
    """
    Flattens SPIRIT, BODY, MIND sections into a list of weekly activity dictionaries.
    Filters out activities if user is on internship and show_for_internship is False.
    """
    result = []
    data = response.get("data", {})
    if not isinstance(data, dict):
        return result

    for aspect, habits in data.items():
        if not isinstance(habits, list):
            continue

        for habit in habits:
            if not isinstance(habit, dict):
                continue

            show_for_internship = habit.get("show_for_internship", True)
            if is_internship and show_for_internship is False:
                continue

            result.append({
                "id": str(habit.get("id", "")),
                "habit": str(habit.get("habit", "")),
                "aspect": str(aspect),
                "type": str(habit.get("type", "WEEKLY")),
                "subtype": str(habit.get("subtype", "HABIT")),
                "details": habit.get("details", []),
                "default_schedule_day": habit.get("default_schedule_day"),
                "activity_type": habit.get("activity_type", "SCHOOL"),
                "show_for_internship": show_for_internship,
                "deeds": habit.get("deeds", {}),
            })

    return result


def get_habit_details(habit: dict) -> List[dict]:
    return habit.get("details", [])


def get_deeds_for_date(habit: dict, activity_date: str) -> List[dict]:
    deeds = habit.get("deeds", {})
    if isinstance(deeds, dict):
        return deeds.get(activity_date, [])
    elif isinstance(deeds, list):
        return [d for d in deeds if isinstance(d, dict) and d.get("date") == activity_date]
    return []


def get_existing_deed(habit: dict, activity_date: str) -> Optional[dict]:
    deeds = get_deeds_for_date(habit, activity_date)
    if deeds and isinstance(deeds[0], dict):
        return deeds[0]
    return None


async def update_weekly_deed(
    client: KejarClient,
    habit_id: str,
    category: str,
    point: int,
    activity_date: str,
    witness_type: Optional[str] = None,
    witness_name: Optional[str] = None,
    deed_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Sends patch request to update weekly habit deed.
    """
    payload = {
        "payloadDeed[habit_id]": str(habit_id),
        "payloadDeed[category]": str(category),
        "payloadDeed[point]": str(point),
        "payloadDeed[date]": str(activity_date),
        "payloadDeed[witnessType]": str(witness_type or ""),
        "payloadDeed[witnessName]": str(witness_name or ""),
        "payloadDeed[deedable_type]": "HABIT",
        "payloadDeed[subtype]": "HABIT",
    }

    if deed_id:
        payload["payloadDeed[deed_id]"] = str(deed_id)

    return await client.patch(UPDATE_WEEKLY_ENDPOINT, data=payload)