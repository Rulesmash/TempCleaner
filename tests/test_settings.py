"""Tests for SettingsStore and DEFAULT_SETTINGS."""

from __future__ import annotations

import json
from pathlib import Path

from tempcleaner.config.defaults import DEFAULT_SETTINGS
from tempcleaner.config.settings import SettingsStore

REQUIRED_DEFAULT_KEYS = {
    "selected_targets",
    "require_dry_run_before_clean",
    "allow_advanced_targets",
    "allow_prefetch_scheduled",
    "scheduled_clean_enabled",
    "scheduled_targets",
    "schedule_frequency",
    "schedule_time",
    "schedule_weekday",
    "close_minimizes",
    "check_updates_on_startup",
    "log_level",
}


def test_default_settings_has_required_keys():
    assert REQUIRED_DEFAULT_KEYS <= set(DEFAULT_SETTINGS.keys())
    assert DEFAULT_SETTINGS["require_dry_run_before_clean"] is True
    assert DEFAULT_SETTINGS["check_updates_on_startup"] is False
    assert DEFAULT_SETTINGS["allow_advanced_targets"] is False
    assert DEFAULT_SETTINGS["allow_prefetch_scheduled"] is False
    assert DEFAULT_SETTINGS["scheduled_clean_enabled"] is False
    assert DEFAULT_SETTINGS["close_minimizes"] is False
    assert DEFAULT_SETTINGS["schedule_frequency"] == "daily"
    assert DEFAULT_SETTINGS["schedule_time"] == "03:00"
    assert DEFAULT_SETTINGS["schedule_weekday"] == "MON"
    assert DEFAULT_SETTINGS["log_level"] == "INFO"
    assert isinstance(DEFAULT_SETTINGS["selected_targets"], list)
    assert isinstance(DEFAULT_SETTINGS["scheduled_targets"], list)


def test_load_returns_defaults_when_missing(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    data = store.load()
    assert data["require_dry_run_before_clean"] is True
    assert data["check_updates_on_startup"] is False
    # All default keys present
    assert REQUIRED_DEFAULT_KEYS <= set(data.keys())


def test_save_and_reload(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    store.save({**store.load(), "close_minimizes": True})
    assert store.load()["close_minimizes"] is True


def test_load_merges_partial_file_with_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps({"close_minimizes": True}), encoding="utf-8")
    store = SettingsStore(path)
    data = store.load()
    assert data["close_minimizes"] is True
    assert data["require_dry_run_before_clean"] is True
    assert data["log_level"] == "INFO"


def test_load_corrupt_json_returns_defaults(tmp_path: Path):
    path = tmp_path / "settings.json"
    path.write_text("{not valid json", encoding="utf-8")
    store = SettingsStore(path)
    data = store.load()
    assert data["require_dry_run_before_clean"] is True
    assert data["check_updates_on_startup"] is False


def test_update_merges_and_persists(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    result = store.update(log_level="DEBUG", close_minimizes=True)
    assert result["log_level"] == "DEBUG"
    assert result["close_minimizes"] is True
    assert result["require_dry_run_before_clean"] is True
    reloaded = store.load()
    assert reloaded["log_level"] == "DEBUG"
    assert reloaded["close_minimizes"] is True


def test_save_creates_parent_directories(tmp_path: Path):
    path = tmp_path / "nested" / "dir" / "settings.json"
    store = SettingsStore(path)
    store.save(store.load())
    assert path.is_file()


def test_load_returns_independent_copy(tmp_path: Path):
    store = SettingsStore(tmp_path / "settings.json")
    a = store.load()
    b = store.load()
    a["close_minimizes"] = True
    a["selected_targets"].append("should_not_leak")
    assert b["close_minimizes"] is False
    assert "should_not_leak" not in b["selected_targets"]
