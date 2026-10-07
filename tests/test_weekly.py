import json
from pathlib import Path
from kejar.weekly import flatten_weekly_habits, get_existing_deed, get_deeds_for_date


def test_flatten_weekly_habits():
    fixture_path = Path(__file__).parent / "fixtures" / "weekly_habituation.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    habits = flatten_weekly_habits(data, is_internship=False)
    assert len(habits) == 3
    names = [h["habit"] for h in habits]
    assert "Sholat Jumat" in names
    assert "Aktivitas Fisik" in names
    assert "Membaca Buku non-pelajaran" in names


def test_show_for_internship_filter():
    fixture_path = Path(__file__).parent / "fixtures" / "weekly_habituation.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    # When user is on internship, show_for_internship=False items should be filtered out
    habits = flatten_weekly_habits(data, is_internship=True)
    assert len(habits) == 2
    names = [h["habit"] for h in habits]
    assert "Membaca Buku non-pelajaran" not in names


def test_existing_deed():
    fixture_path = Path(__file__).parent / "fixtures" / "weekly_habituation.json"
    with open(fixture_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    habits = flatten_weekly_habits(data, is_internship=False)
    sholat_jumat = [h for h in habits if h["habit"] == "Sholat Jumat"][0]

    deed = get_existing_deed(sholat_jumat, "2026-10-02")
    assert deed is not None
    assert deed["id"] == "deed_weekly_001"

    no_deed = get_existing_deed(sholat_jumat, "2026-10-03")
    assert no_deed is None
