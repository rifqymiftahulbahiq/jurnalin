import os
import pytest
from database import init_database, save_weekly_activity_setting, get_weekly_activity_settings
from handlers.settings import DEFAULT_WEEKLY_ACTIVITIES


def test_weekly_witness_settings(tmp_path, monkeypatch):
    test_db = os.path.join(tmp_path, "test_settings.db")
    monkeypatch.setattr("database.DATABASE_PATH", test_db)
    init_database()

    user_id = 998877

    # Test saving witness type for single activity
    save_weekly_activity_setting(user_id, "Aktivitas Fisik", "Aktivitas Fisik", 1, witness_type="Guru", witness_name="")
    settings = get_weekly_activity_settings(user_id)
    assert "Aktivitas Fisik" in settings
    assert settings["Aktivitas Fisik"]["witness_type"] == "Guru"

    # Test saving witness for all activities
    for act in DEFAULT_WEEKLY_ACTIVITIES:
        save_weekly_activity_setting(user_id, act, act, 1, witness_type="Orang Tua", witness_name="")

    settings_all = get_weekly_activity_settings(user_id)
    assert len(settings_all) == len(DEFAULT_WEEKLY_ACTIVITIES)
    for act in DEFAULT_WEEKLY_ACTIVITIES:
        assert settings_all[act]["witness_type"] == "Orang Tua"
