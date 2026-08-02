"""Default application settings for TempCleaner."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


DEFAULT_SETTINGS: dict[str, Any] = {
    "selected_targets": ["user_temp", "windows_temp"],
    "require_dry_run_before_clean": True,
    "allow_advanced_targets": False,
    "allow_prefetch_scheduled": False,
    "scheduled_clean_enabled": False,
    "scheduled_targets": [],
    "schedule_frequency": "daily",
    "schedule_time": "03:00",
    "schedule_weekday": "MON",
    "close_minimizes": False,
    "check_updates_on_startup": False,
    "log_level": "INFO",
}


def default_settings_copy() -> dict[str, Any]:
    """Return a deep copy of DEFAULT_SETTINGS for safe mutation."""
    return deepcopy(DEFAULT_SETTINGS)
