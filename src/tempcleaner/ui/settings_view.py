"""Settings tab: toggles bound to SettingsStore with Save / Reset."""

from __future__ import annotations

import logging
import os
import subprocess
import threading
import tkinter as tk
import webbrowser
from collections.abc import Callable
from pathlib import Path
from tkinter import messagebox, ttk
from typing import Any

from tempcleaner.config.defaults import default_settings_copy
from tempcleaner.config.settings import SettingsStore
from tempcleaner.platform_win.paths import appdata_dir
from tempcleaner.platform_win.updates import check_latest_release
from tempcleaner.ui.dialogs import about_dialog
from tempcleaner.version import __version__

logger = logging.getLogger("tempcleaner.ui.settings_view")

# Boolean settings exposed as checkboxes (label, key)
_BOOL_TOGGLES: tuple[tuple[str, str], ...] = (
    ("Require dry-run before clean", "require_dry_run_before_clean"),
    ("Allow advanced targets", "allow_advanced_targets"),
    ("Allow Prefetch in scheduled runs", "allow_prefetch_scheduled"),
    ("Close minimizes to tray-less minimize", "close_minimizes"),
    ("Check for updates on startup", "check_updates_on_startup"),
)


class SettingsView(ttk.Frame):
    """Edit preference toggles and persist via :class:`SettingsStore`."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        store: SettingsStore,
        settings: dict[str, Any],
        on_settings_saved: Callable[[dict[str, Any]], None] | None = None,
        on_exit: Callable[[], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        self._store = store
        self._settings = dict(settings)
        self._on_settings_saved = on_settings_saved
        self._on_exit = on_exit
        self._bool_vars: dict[str, tk.BooleanVar] = {}
        self._log_level_var = tk.StringVar(value=str(settings.get("log_level", "INFO")))
        self._status_var = tk.StringVar(value="")
        self._build()
        self.load_from_settings(self._settings)

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        ttk.Label(
            self,
            text="Preferences are stored under %AppData%\\TempCleaner\\settings.json",
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        body = ttk.LabelFrame(self, text="Options", padding=10)
        body.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        body.columnconfigure(0, weight=1)

        row = 0
        for label, key in _BOOL_TOGGLES:
            var = tk.BooleanVar(value=False)
            self._bool_vars[key] = var
            ttk.Checkbutton(body, text=label, variable=var).grid(
                row=row, column=0, sticky="w", pady=2
            )
            row += 1

        level_row = ttk.Frame(body)
        level_row.grid(row=row, column=0, sticky="w", pady=(10, 2))
        ttk.Label(level_row, text="Log level:").grid(row=0, column=0, sticky="w")
        level_combo = ttk.Combobox(
            level_row,
            textvariable=self._log_level_var,
            values=("DEBUG", "INFO", "WARNING", "ERROR"),
            state="readonly",
            width=12,
        )
        level_combo.grid(row=0, column=1, sticky="w", padx=(8, 0))

        folders = ttk.LabelFrame(self, text="Folders", padding=10)
        folders.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            folders, text="Open settings folder", command=self._open_settings_folder
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(
            folders, text="Open logs folder", command=self._open_logs_folder
        ).grid(row=0, column=1)

        updates = ttk.LabelFrame(self, text="Updates & about", padding=10)
        updates.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(
            updates, text="Check for updates", command=self._on_check_updates
        ).grid(row=0, column=0, padx=(0, 8))
        ttk.Button(updates, text="About…", command=self._on_about).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Button(
            updates, text="Exit application", command=self._on_exit_application
        ).grid(row=0, column=2)

        actions = ttk.Frame(self)
        actions.grid(row=4, column=0, sticky="ew")
        actions.columnconfigure(2, weight=1)

        ttk.Button(actions, text="Save", command=self._on_save).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(actions, text="Reset to defaults", command=self._on_reset).grid(
            row=0, column=1, padx=(0, 8)
        )
        ttk.Label(actions, textvariable=self._status_var).grid(
            row=0, column=2, sticky="e"
        )

    def load_from_settings(self, settings: dict[str, Any]) -> None:
        """Refresh checkbox/combobox widgets from a settings dict."""
        self._settings = dict(settings)
        for key, var in self._bool_vars.items():
            var.set(bool(settings.get(key, False)))
        level = str(settings.get("log_level", "INFO")).upper()
        if level not in ("DEBUG", "INFO", "WARNING", "ERROR"):
            level = "INFO"
        self._log_level_var.set(level)
        self._status_var.set("")

    def collect_settings(self) -> dict[str, Any]:
        """Merge UI values into a full settings dict (preserving other keys)."""
        data = dict(self._settings)
        for key, var in self._bool_vars.items():
            data[key] = bool(var.get())
        data["log_level"] = str(self._log_level_var.get() or "INFO").upper()
        return data

    def _on_save(self) -> None:
        data = self.collect_settings()
        try:
            self._store.save(data)
        except OSError as exc:
            logger.warning("Settings save failed: %s", exc)
            messagebox.showerror(
                "Save failed",
                f"Could not write settings:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        self._settings = data
        self._status_var.set("Saved.")
        logger.info("Settings saved to %s", self._store.path)
        if self._on_settings_saved is not None:
            self._on_settings_saved(dict(data))

    def _on_reset(self) -> None:
        if not messagebox.askyesno(
            "Reset settings",
            "Reset all preferences to defaults?\n\n"
            "Defaults will be applied and saved to settings.json immediately.",
            parent=self.winfo_toplevel(),
        ):
            return
        data = default_settings_copy()
        # Keep selected_targets / schedule keys from defaults fully
        try:
            self._store.save(data)
        except OSError as exc:
            logger.warning("Settings reset save failed: %s", exc)
            messagebox.showerror(
                "Reset failed",
                f"Could not write defaults:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        self.load_from_settings(data)
        self._status_var.set("Defaults restored and saved.")
        logger.info("Settings reset to defaults at %s", self._store.path)
        if self._on_settings_saved is not None:
            self._on_settings_saved(dict(data))

    def _on_exit_application(self) -> None:
        """Always exit (destroy main window); ignores close_minimizes."""
        if self._on_exit is not None:
            self._on_exit()
            return
        try:
            self.winfo_toplevel().destroy()
        except tk.TclError:
            pass

    def _on_about(self) -> None:
        about_dialog(
            self.winfo_toplevel(),
            on_check_updates=self._on_check_updates,
        )

    def _on_check_updates(self) -> None:
        """Run GitHub Releases check off the UI thread; show result via messagebox."""
        self._status_var.set("Checking for updates…")
        parent = self.winfo_toplevel()

        def work() -> None:
            result = check_latest_release(__version__)
            parent.after(0, lambda: self._show_update_result(result))

        threading.Thread(target=work, name="tc-update-check", daemon=True).start()

    def _show_update_result(
        self, result: tuple[bool, str | None, str | None]
    ) -> None:
        available, latest_tag, html_url = result
        parent = self.winfo_toplevel()
        if latest_tag is None:
            self._status_var.set("Update check failed (offline or error).")
            messagebox.showinfo(
                "Update check",
                "Could not check for updates.\n\n"
                "You may be offline, or GitHub is unreachable.\n"
                f"Current version: {__version__}",
                parent=parent,
            )
            return

        if available:
            self._status_var.set(f"Update available: {latest_tag}")
            msg = (
                f"A newer release is available.\n\n"
                f"Current: {__version__}\n"
                f"Latest:  {latest_tag}\n"
            )
            if html_url:
                msg += f"\nOpen release page?\n{html_url}"
                if messagebox.askyesno("Update available", msg, parent=parent):
                    try:
                        webbrowser.open(html_url)
                    except OSError as exc:
                        logger.warning("Could not open browser: %s", exc)
            else:
                messagebox.showinfo("Update available", msg, parent=parent)
        else:
            self._status_var.set(f"Up to date ({latest_tag}).")
            messagebox.showinfo(
                "Update check",
                f"You are on the latest release.\n\n"
                f"Current: {__version__}\n"
                f"Latest:  {latest_tag}",
                parent=parent,
            )

    def _open_settings_folder(self) -> None:
        path = self._store.path.parent
        self._open_folder(path)

    def _open_logs_folder(self) -> None:
        path = appdata_dir() / "logs"
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                "Open folder failed",
                f"Could not create logs folder:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        self._open_folder(path)

    def _open_folder(self, path: Path) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                "Open folder failed",
                f"Could not access folder:\n{path}\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except OSError:
            try:
                subprocess.run(
                    ["explorer", str(path)],
                    check=False,
                    capture_output=True,
                )
            except OSError as exc:
                messagebox.showerror(
                    "Open folder failed",
                    f"Could not open:\n{path}\n\n{exc}",
                    parent=self.winfo_toplevel(),
                )
