"""Windows platform helpers (paths, elevation, scheduler, updates)."""

from tempcleaner.platform_win.admin import is_admin, relaunch_as_admin
from tempcleaner.platform_win.scheduler import (
    TASK_NAME,
    install_schedule,
    remove_schedule,
    schedule_exists,
)

__all__ = [
    "TASK_NAME",
    "is_admin",
    "install_schedule",
    "relaunch_as_admin",
    "remove_schedule",
    "schedule_exists",
]
