"""Windows platform helpers (paths, elevation, scheduler, updates)."""

from tempcleaner.platform_win.admin import is_admin, relaunch_as_admin

__all__ = [
    "is_admin",
    "relaunch_as_admin",
]
