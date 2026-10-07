from datetime import date
from database import (
    init_database,
    create_or_update_user,
    save_user_mebs,
    save_meb_target
)
from kejar.meb import MebPeriod
from services.planner import generate_journal_plan
from kejar.behavior import get_behavior_journal_status


def test_dry_run_planner():
    init_database()
    test_user_id = 999111

    create_or_update_user(test_user_id, username="testuser", first_name="Test")
    save_meb_target(test_user_id, start_meb=8, end_meb=9)

    mebs = [
        MebPeriod(
            id="sw_008",
            report_period_id="rp_01",
            number=8,
            label="MEB 8",
            start_date=date(2026, 9, 21),
            end_date=date(2026, 9, 27),
            school_week="39",
            is_matrikulasi=False
        ),
        MebPeriod(
            id="sw_009",
            report_period_id="rp_01",
            number=9,
            label="MEB 9",
            start_date=date(2026, 9, 28),
            end_date=date(2026, 10, 4),
            school_week="40",
            is_matrikulasi=False
        )
    ]
    save_user_mebs(test_user_id, mebs)

    today = date(2026, 10, 2)
    plan = generate_journal_plan(test_user_id, today=today)

    assert plan["target_range"] == "MEB 8 → MEB 9"
    assert plan["total_mebs"] == 2
    # MEB 8: 7 days eligible. MEB 9: 5 days eligible (28, 29, 30, 01, 02). Total = 12
    assert plan["total_eligible_days"] == 12


def test_behavior_journal_safety():
    status = get_behavior_journal_status()
    assert status["touched"] is False
    assert status["action"] == "SKIP"
    assert "🚫 Jurnal Perilaku tidak disentuh." in status["message"]
