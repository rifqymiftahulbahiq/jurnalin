from typing import Dict, List, Any
from kejar.meb import parse_meb_response, MebPeriod
from kejar.daily import parse_daily_response
from kejar.weekly import flatten_weekly_habits
from kejar.non_routine import parse_non_routine


class KejarDataParser:
    @staticmethod
    def parse_meb(response: dict) -> List[MebPeriod]:
        return parse_meb_response(response)

    @staticmethod
    def parse_daily(response: dict) -> List[Dict[str, Any]]:
        return parse_daily_response(response)

    @staticmethod
    def parse_weekly(response: dict, is_internship: bool = False) -> List[Dict[str, Any]]:
        return flatten_weekly_habits(response, is_internship=is_internship)

    @staticmethod
    def parse_non_routine(response: dict) -> List[Dict[str, Any]]:
        return parse_non_routine(response)
