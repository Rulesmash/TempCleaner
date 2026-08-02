"""Application configuration: defaults and JSON settings store."""

from tempcleaner.config.defaults import DEFAULT_SETTINGS, default_settings_copy
from tempcleaner.config.settings import SettingsStore

__all__ = [
    "DEFAULT_SETTINGS",
    "SettingsStore",
    "default_settings_copy",
]
