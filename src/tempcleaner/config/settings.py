"""JSON settings store under AppData (path injectable for tests)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tempcleaner.config.defaults import default_settings_copy
from tempcleaner.platform_win.paths import appdata_dir


class SettingsStore:
    """Load, save, and update application settings as JSON.

    Default path is ``appdata_dir() / "settings.json"``. Pass an explicit
    ``path`` (e.g. under ``tmp_path``) in tests.
    """

    def __init__(self, path: Path | None = None) -> None:
        self.path: Path = path if path is not None else appdata_dir() / "settings.json"

    def load(self) -> dict[str, Any]:
        """Return settings merged with defaults.

        Missing file or unreadable/corrupt JSON yields a full defaults copy.
        Partial files are shallow-merged so unknown keys are kept and missing
        known keys fall back to defaults.
        """
        data = default_settings_copy()
        if not self.path.is_file():
            return data
        try:
            raw = self.path.read_text(encoding="utf-8")
            loaded = json.loads(raw)
        except (OSError, UnicodeError, json.JSONDecodeError):
            return data
        if not isinstance(loaded, dict):
            return data
        data.update(loaded)
        return data

    def save(self, data: dict[str, Any]) -> None:
        """Persist *data* as JSON, creating parent directories as needed."""
        self.path.parent.mkdir(parents=True, exist_ok=True)
        text = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
        self.path.write_text(text, encoding="utf-8")

    def update(self, **kwargs: Any) -> dict[str, Any]:
        """Load, apply keyword updates, save, and return the new dict."""
        data = self.load()
        data.update(kwargs)
        self.save(data)
        return data
