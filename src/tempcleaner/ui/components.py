"""Reusable ttk widgets and UI helpers for TempCleaner."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable

from tempcleaner.core.models import RiskLevel


def risk_tag_text(risk: RiskLevel) -> str:
    """Short risk label for target rows."""
    if risk is RiskLevel.SAFE:
        return "Safe"
    if risk is RiskLevel.ELEVATED:
        return "Elevated"
    if risk is RiskLevel.ADVANCED:
        return "Advanced"
    return str(risk.value).title()


class AdminBadge(ttk.Frame):
    """Shows Elevated / Standard user and optional Restart as admin button."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        is_elevated: bool,
        on_relaunch: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        self._is_elevated = is_elevated
        self._on_relaunch = on_relaunch

        self._badge = ttk.Label(self, text="", padding=(8, 2))
        self._badge.grid(row=0, column=0, padx=(0, 8))

        self._relaunch_btn = ttk.Button(
            self,
            text="Restart as admin",
            command=self._handle_relaunch,
        )
        self._relaunch_btn.grid(row=0, column=1)

        self.set_elevated(is_elevated)

    def set_elevated(self, elevated: bool) -> None:
        self._is_elevated = elevated
        if elevated:
            self._badge.configure(text="Elevated")
            self._relaunch_btn.state(["disabled"])
        else:
            self._badge.configure(text="Standard user")
            self._relaunch_btn.state(["!disabled"])

    def _handle_relaunch(self) -> None:
        if self._on_relaunch is not None:
            self._on_relaunch()


class StatusBar(ttk.Frame):
    """Bottom status line for last action / busy text."""

    def __init__(self, parent: tk.Misc, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        self.columnconfigure(0, weight=1)
        ttk.Separator(self, orient="horizontal").grid(row=0, column=0, sticky="ew")
        self._label = ttk.Label(self, text="Ready", anchor="w", padding=(8, 4))
        self._label.grid(row=1, column=0, sticky="ew")

    def set_text(self, text: str) -> None:
        self._label.configure(text=text)


class PlaceholderTab(ttk.Frame):
    """Simple placeholder pane for tabs implemented in later tasks."""

    def __init__(self, parent: tk.Misc, title: str, note: str = "", **kwargs: object) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        msg = note or f"{title} tab — coming in a later build."
        ttk.Label(self, text=msg, padding=24).pack(expand=True)
