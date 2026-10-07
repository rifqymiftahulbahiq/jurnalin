import json
from datetime import date
from pathlib import Path
from kejar.meb import parse_meb_response, filter_target_mebs, eligible_dates


def test_parse_meb_response():
    fixture_path = Path(__file__).parent / "fixtures" / "meb_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mebs = parse_meb_response(data)
    assert len(mebs) == 3
    assert mebs[0].number == 8
    assert mebs[1].number == 9
    assert mebs[2].number == 10
    assert mebs[1].label == "MEB 9"
    assert mebs[1].start_date == date(2026, 9, 28)
    assert mebs[1].end_date == date(2026, 10, 4)


def test_filter_target_mebs():
    fixture_path = Path(__file__).parent / "fixtures" / "meb_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mebs = parse_meb_response(data)
    filtered = filter_target_mebs(mebs, start_number=8, end_number=9)
    assert len(filtered) == 2
    assert [m.number for m in filtered] == [8, 9]


def test_eligible_dates():
    fixture_path = Path(__file__).parent / "fixtures" / "meb_response.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    mebs = parse_meb_response(data)
    meb9 = [m for m in mebs if m.number == 9][0]

    # Test when today is inside MEB 9 (e.g. 2026-10-02)
    today = date(2026, 10, 2)
    dates = eligible_dates(meb9, today)

    assert len(dates) == 5
    assert dates[0] == date(2026, 9, 28)
    assert dates[-1] == date(2026, 10, 2)
    assert date(2026, 10, 3) not in dates
    assert date(2026, 10, 4) not in dates

    # Test when today is before MEB start
    early_today = date(2026, 9, 20)
    assert eligible_dates(meb9, early_today) == []

    # Test when today is after MEB end (e.g. 2026-10-10)
    late_today = date(2026, 10, 10)
    assert len(eligible_dates(meb9, late_today)) == 7
