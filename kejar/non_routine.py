from typing import Dict, List, Any


def parse_non_routine(response: dict) -> List[Dict[str, Any]]:
    """
    Parses Non-Routine activities response.
    Returns empty list if no scheduled non-routine activities exist.
    """
    data = response.get("data", [])
    if not data or response.get("message") == "Belum ada kegiatan yang dijadwalkan.":
        return []

    activities = []
    if isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                activities.append({
                    "id": item.get("id"),
                    "title": item.get("title", item.get("name")),
                    "schedule": item.get("schedule"),
                    "status": item.get("status")
                })
    return activities
