import json
from pathlib import Path
from kejar.daily import parse_daily_response


def test_parse_daily_response():
    fixture_path = Path(__file__).parent / "fixtures" / "daily_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    items = parse_daily_response(data)
    assert len(items) == 2
    assert items[0]["name"] == "Salat Subuh"
    assert items[0]["deed_id"] == "deed_daily_010"
    assert items[1]["name"] == "Zikir Pagi"
    assert items[1]["deed_id"] is None
