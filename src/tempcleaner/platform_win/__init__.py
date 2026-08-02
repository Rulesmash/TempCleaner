"""Windows platform helpers (paths, elevation, scheduler, updates)."""

from tempcleaner.platform_win.admin import is_admin, relaunch_as_admin
from tempcleaner.platform_win.scheduler import (
    TASK_NAME,
    install_schedule,
    remove_schedule,
    schedule_exists,
)
from tempcleaner.platform_win.updates import (
    check_latest_release,
    is_newer,
    version_tuple,
)

__all__ = [
    "TASK_NAME",
    "check_latest_release",
    "install_schedule",
    "is_admin",
    "is_newer",
    "relaunch_as_admin",
    "remove_schedule",
    "schedule_exists",
    "version_tuple",
]
