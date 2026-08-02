"""Well-known Windows paths used by clean targets and app data."""

from __future__ import annotations

import os
from pathlib import Path


def user_temp() -> Path:
    temp = os.environ.get("TEMP") or os.environ.get("TMP")
    if temp:
        return Path(temp)
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Temp"
    return Path.home() / "AppData" / "Local" / "Temp"


def windows_temp() -> Path:
    return Path(r"C:\Windows\Temp")


def prefetch() -> Path:
    return Path(r"C:\Windows\Prefetch")


def recent_dir() -> Path:
    return Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Recent"


def thumbcache_dir() -> Path:
    local = os.environ.get("LOCALAPPDATA")
    if local:
        return Path(local) / "Microsoft" / "Windows" / "Explorer"
    return Path.home() / "AppData" / "Local" / "Microsoft" / "Windows" / "Explorer"


def delivery_optimization() -> Path:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return (
        Path(system_root)
        / "ServiceProfiles"
        / "NetworkService"
        / "AppData"
        / "Local"
        / "Microsoft"
        / "Windows"
        / "DeliveryOptimization"
        / "Cache"
    )


def windows_update_download() -> Path:
    system_root = os.environ.get("SystemRoot", r"C:\Windows")
    return Path(system_root) / "SoftwareDistribution" / "Download"


def appdata_dir() -> Path:
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / "TempCleaner"
    return Path.home() / "AppData" / "Roaming" / "TempCleaner"


def get_known_paths() -> dict[str, Path]:
    return {
        "user_temp": user_temp(),
        "windows_temp": windows_temp(),
        "prefetch": prefetch(),
        "recent": recent_dir(),
        "thumbcache": thumbcache_dir(),
        "delivery_optimization": delivery_optimization(),
        "windows_update_download": windows_update_download(),
        "appdata": appdata_dir(),
    }
