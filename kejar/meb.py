from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Dict, Optional, Any


@dataclass
class MebPeriod:
    id: str
    report_period_id: str
    number: int
    label: str
    start_date: date
    end_date: date
    school_week: str
    is_matrikulasi: bool
    school_week_id: Optional[str] = None

    def __post_init__(self):
        if not self.school_week_id:
            self.school_week_id = self.id


def parse_kejar_date(value: Optional[str]) -> Optional[date]:
    if not value:
        return None
    try:
        return date.fromisoformat(value[:10])
    except Exception:
        return None


def parse_school_week(data: dict) -> MebPeriod:
    s_date = parse_kejar_date(data.get("start_date"))
    e_date = parse_kejar_date(data.get("end_date"))
    if not s_date or not e_date:
        raise ValueError("Invalid dates in school week data")

    return MebPeriod(
        id=str(data.get("id", "")),
        report_period_id=str(data.get("report_period_id", "")),
        number=int(data.get("order", 0)),
        label=str(data.get("label", f"MEB {data.get('order', '')}")),
        start_date=s_date,
        end_date=e_date,
        school_week=str(data.get("week", "")),
        is_matrikulasi=bool(data.get("is_matrikulasi", False)),
        school_week_id=str(data.get("id", ""))
    )


def parse_meb_response(response: dict) -> List[MebPeriod]:
    result = []
    # Unwrap data key if wrapped
    target_dict = response.get("data", response) if isinstance(response.get("data"), dict) else response

    keys = ["previous_school_week", "current_school_week", "next_school_week"]
    for key in keys:
        item = target_dict.get(key)
        if isinstance(item, dict):
            try:
                meb = parse_school_week(item)
                result.append(meb)
            except (KeyError, TypeError, ValueError):
                continue

    # Also handle array data if response contains list of school weeks
    sw_list = target_dict.get("school_weeks") or response.get("school_weeks") or (response.get("data") if isinstance(response.get("data"), list) else None)
    if isinstance(sw_list, list):
        for item in sw_list:
            if isinstance(item, dict):
                try:
                    meb = parse_school_week(item)
                    result.append(meb)
                except Exception:
                    continue

    unique = {}
    for meb in result:
        unique[meb.number] = meb

    return sorted(unique.values(), key=lambda item: item.number)


def filter_target_mebs(mebs: List[MebPeriod], start_number: int, end_number: int) -> List[MebPeriod]:
    return [
        meb for meb in mebs
        if start_number <= meb.number <= end_number
    ]


def eligible_dates(meb: MebPeriod, today: date) -> List[date]:
    """
    Returns list of dates within MEB range that are <= today.
    Dates strictly after today are NOT eligible.
    """
    if today < meb.start_date:
        return []

    last_date = min(meb.end_date, today)
    if last_date < meb.start_date:
        return []

    dates = []
    current = meb.start_date
    while current <= last_date:
        dates.append(current)
        current += timedelta(days=1)

    return dates


def format_meb(meb: MebPeriod) -> str:
    return (
        f"{meb.label}\n"
        f"📅 {meb.start_date.strftime('%d-%m-%Y')} → {meb.end_date.strftime('%d-%m-%Y')}"
    )


def format_eligible_dates(meb: MebPeriod, today: date) -> str:
    dates = eligible_dates(meb, today)
    if not dates:
        return f"{meb.label}: belum ada tanggal yang bisa diproses."

    date_text = ", ".join(item.strftime("%d-%m") for item in dates)
    return f"{meb.label}: {date_text}"