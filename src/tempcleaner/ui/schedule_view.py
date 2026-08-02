"""Schedule tab: enable Task Scheduler clean, frequency/time, apply/remove."""

from __future__ import annotations

import logging
import re
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox, ttk
from typing import Any

from tempcleaner.config.settings import SettingsStore
from tempcleaner.platform_win.scheduler import (
    TASK_NAME,
    build_scheduled_command,
    install_schedule,
    remove_schedule,
    schedule_exists,
)

logger = logging.getLogger("tempcleaner.ui.schedule_view")

_FREQUENCIES = ("daily", "weekly")
_WEEKDAYS = ("MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN")
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class ScheduleView(ttk.Frame):
    """Configure and install/remove the Windows scheduled clean task.

    On Apply with enable checked, persists the current Clean-tab selection into
    ``scheduled_targets`` and sets ``scheduled_clean_enabled``.
    """

    def __init__(
        self,
        parent: tk.Misc,
        *,
        store: SettingsStore,
        settings: dict[str, Any],
        get_selected_targets: Callable[[], list[str]],
        on_settings_updated: Callable[[dict[str, Any]], None] | None = None,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        self._store = store
        self._settings = dict(settings)
        self._get_selected_targets = get_selected_targets
        self._on_settings_updated = on_settings_updated

        self._enabled_var = tk.BooleanVar(value=False)
        self._frequency_var = tk.StringVar(value="daily")
        self._time_var = tk.StringVar(value="03:00")
        self._weekday_var = tk.StringVar(value="MON")
        self._status_var = tk.StringVar(value="")
        self._detail_var = tk.StringVar(value="")
        self._message_var = tk.StringVar(value="")

        self._build()
        self.load_from_settings(self._settings)
        self.refresh_status()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)

        ttk.Label(
            self,
            text=(
                "Schedule a headless clean via Windows Task Scheduler. "
                f'Task name: "{TASK_NAME}".'
            ),
            wraplength=720,
        ).grid(row=0, column=0, sticky="w", pady=(0, 8))

        opts = ttk.LabelFrame(self, text="Schedule options", padding=10)
        opts.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        opts.columnconfigure(1, weight=1)

        self._enabled_cb = ttk.Checkbutton(
            opts,
            text="Enable scheduled clean",
            variable=self._enabled_var,
            command=self._on_enable_toggled,
        )
        self._enabled_cb.grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

        ttk.Label(opts, text="Frequency:").grid(row=1, column=0, sticky="w", pady=2)
        self._freq_combo = ttk.Combobox(
            opts,
            textvariable=self._frequency_var,
            values=_FREQUENCIES,
            state="readonly",
            width=12,
        )
        self._freq_combo.grid(row=1, column=1, sticky="w", padx=(8, 0), pady=2)
        self._freq_combo.bind("<<ComboboxSelected>>", self._on_frequency_changed)

        ttk.Label(opts, text="Time (HH:MM):").grid(row=2, column=0, sticky="w", pady=2)
        self._time_entry = ttk.Entry(opts, textvariable=self._time_var, width=10)
        self._time_entry.grid(row=2, column=1, sticky="w", padx=(8, 0), pady=2)

        ttk.Label(opts, text="Weekday:").grid(row=3, column=0, sticky="w", pady=2)
        self._weekday_combo = ttk.Combobox(
            opts,
            textvariable=self._weekday_var,
            values=_WEEKDAYS,
            state="readonly",
            width=12,
        )
        self._weekday_combo.grid(row=3, column=1, sticky="w", padx=(8, 0), pady=2)

        note = ttk.Label(
            opts,
            text=(
                "Apply uses the current Clean tab selection as scheduled_targets "
                "and installs/updates the Task Scheduler entry."
            ),
            foreground="gray",
            wraplength=680,
        )
        note.grid(row=4, column=0, columnspan=2, sticky="w", pady=(10, 0))

        status_box = ttk.LabelFrame(self, text="Task status", padding=10)
        status_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        status_box.columnconfigure(0, weight=1)

        ttk.Label(
            status_box,
            textvariable=self._status_var,
            font=("", 10, "bold"),
        ).grid(row=0, column=0, sticky="w")
        ttk.Label(
            status_box,
            textvariable=self._detail_var,
            foreground="gray",
            wraplength=700,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 0))

        actions = ttk.Frame(self)
        actions.grid(row=3, column=0, sticky="ew")
        actions.columnconfigure(3, weight=1)

        self._apply_btn = ttk.Button(
            actions, text="Apply schedule", command=self._on_apply
        )
        self._apply_btn.grid(row=0, column=0, padx=(0, 8))

        self._remove_btn = ttk.Button(
            actions, text="Remove schedule", command=self._on_remove
        )
        self._remove_btn.grid(row=0, column=1, padx=(0, 8))

        self._refresh_btn = ttk.Button(
            actions, text="Refresh status", command=self.refresh_status
        )
        self._refresh_btn.grid(row=0, column=2, padx=(0, 8))

        ttk.Label(actions, textvariable=self._message_var).grid(
            row=0, column=3, sticky="e"
        )

        self._sync_weekday_state()

    # ----------------------------------------------------------------- public
    def load_from_settings(self, settings: dict[str, Any]) -> None:
        """Refresh widgets from a settings dict."""
        self._settings = dict(settings)
        self._enabled_var.set(bool(settings.get("scheduled_clean_enabled", False)))
        freq = str(settings.get("schedule_frequency", "daily")).strip().lower()
        if freq not in _FREQUENCIES:
            freq = "daily"
        self._frequency_var.set(freq)
        time_s = str(settings.get("schedule_time", "03:00")).strip()
        if not _TIME_RE.match(time_s):
            time_s = "03:00"
        self._time_var.set(time_s)
        day = str(settings.get("schedule_weekday", "MON")).strip().upper()
        if day not in _WEEKDAYS:
            day = "MON"
        self._weekday_var.set(day)
        self._message_var.set("")
        self._sync_weekday_state()

    def refresh_status(self) -> None:
        """Query Task Scheduler and update the status label."""
        try:
            exists = schedule_exists()
        except OSError as exc:
            self._status_var.set("Status unknown")
            self._detail_var.set(f"Could not query schtasks: {exc}")
            logger.warning("schedule_exists failed: %s", exc)
            return

        enabled = bool(self._settings.get("scheduled_clean_enabled", False))
        targets = self._settings.get("scheduled_targets") or []
        if not isinstance(targets, list):
            targets = []
        target_txt = ", ".join(str(t) for t in targets) if targets else "(none)"
        freq = self._settings.get("schedule_frequency", "daily")
        time_s = self._settings.get("schedule_time", "03:00")
        day = self._settings.get("schedule_weekday", "MON")
        when = f"{freq} at {time_s}"
        if str(freq).lower() == "weekly":
            when = f"weekly ({day}) at {time_s}"

        if exists:
            self._status_var.set("Registered in Task Scheduler")
        else:
            self._status_var.set("Not registered in Task Scheduler")

        self._detail_var.set(
            f"Settings enabled={enabled}; when={when}; "
            f"scheduled_targets=[{target_txt}]; "
            f"command={build_scheduled_command()}"
        )

    # ----------------------------------------------------------------- events
    def _on_enable_toggled(self) -> None:
        self._message_var.set("")

    def _on_frequency_changed(self, _event: object = None) -> None:
        self._sync_weekday_state()

    def _sync_weekday_state(self) -> None:
        weekly = str(self._frequency_var.get()).lower() == "weekly"
        state = "readonly" if weekly else "disabled"
        try:
            self._weekday_combo.configure(state=state)
        except tk.TclError:
            pass

    def _on_apply(self) -> None:
        enabled = bool(self._enabled_var.get())
        freq = str(self._frequency_var.get()).strip().lower()
        time_s = str(self._time_var.get()).strip()
        weekday = str(self._weekday_var.get()).strip().upper()

        if freq not in _FREQUENCIES:
            messagebox.showerror(
                "Invalid frequency",
                "Choose daily or weekly.",
                parent=self.winfo_toplevel(),
            )
            return
        if not _TIME_RE.match(time_s):
            messagebox.showerror(
                "Invalid time",
                "Time must be 24-hour HH:MM (e.g. 03:00 or 14:30).",
                parent=self.winfo_toplevel(),
            )
            return
        if freq == "weekly" and weekday not in _WEEKDAYS:
            messagebox.showerror(
                "Invalid weekday",
                "Choose a weekday for weekly schedules.",
                parent=self.winfo_toplevel(),
            )
            return

        data = dict(self._settings)
        data["schedule_frequency"] = freq
        data["schedule_time"] = time_s
        data["schedule_weekday"] = weekday if freq == "weekly" else data.get(
            "schedule_weekday", "MON"
        )

        if enabled:
            selected = list(self._get_selected_targets())
            if not selected:
                messagebox.showinfo(
                    "No targets",
                    "Select at least one target on the Clean tab before applying "
                    "an enabled schedule.\n\nApply uses the current Clean selection "
                    "as scheduled_targets.",
                    parent=self.winfo_toplevel(),
                )
                return
            data["scheduled_clean_enabled"] = True
            data["scheduled_targets"] = selected
            command = build_scheduled_command()
            try:
                install_schedule(
                    frequency=freq,
                    time_hhmm=time_s,
                    weekday=weekday if freq == "weekly" else None,
                    command=command,
                )
            except (ValueError, RuntimeError, OSError) as exc:
                logger.warning("install_schedule failed: %s", exc)
                messagebox.showerror(
                    "Schedule failed",
                    f"Could not create/update the scheduled task.\n\n{exc}\n\n"
                    "Creating tasks may require administrator rights.",
                    parent=self.winfo_toplevel(),
                )
                return
        else:
            data["scheduled_clean_enabled"] = False
            # Keep last scheduled_targets for reference; still remove OS task
            try:
                remove_schedule()
            except (RuntimeError, OSError) as exc:
                logger.warning("remove_schedule (disabled apply) failed: %s", exc)
                messagebox.showerror(
                    "Remove failed",
                    f"Settings will not be saved until the task can be updated.\n\n{exc}",
                    parent=self.winfo_toplevel(),
                )
                return

        try:
            self._store.save(data)
        except OSError as exc:
            logger.warning("Schedule settings save failed: %s", exc)
            messagebox.showerror(
                "Save failed",
                f"Task was updated but settings could not be saved:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            # Still refresh status; settings may be stale
            self.refresh_status()
            return

        self._settings = data
        self._message_var.set("Applied.")
        logger.info(
            "Schedule applied: enabled=%s freq=%s time=%s targets=%s",
            data.get("scheduled_clean_enabled"),
            freq,
            time_s,
            data.get("scheduled_targets"),
        )
        if self._on_settings_updated is not None:
            self._on_settings_updated(dict(data))
        self.refresh_status()

    def _on_remove(self) -> None:
        if not messagebox.askyesno(
            "Remove schedule",
            f'Remove Task Scheduler task "{TASK_NAME}" and disable '
            "scheduled_clean_enabled in settings?",
            parent=self.winfo_toplevel(),
        ):
            return
        try:
            remove_schedule()
        except (RuntimeError, OSError) as exc:
            logger.warning("remove_schedule failed: %s", exc)
            messagebox.showerror(
                "Remove failed",
                f"Could not remove the scheduled task.\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return

        data = dict(self._settings)
        data["scheduled_clean_enabled"] = False
        try:
            self._store.save(data)
        except OSError as exc:
            logger.warning("Schedule disable save failed: %s", exc)
            messagebox.showerror(
                "Save failed",
                f"Task removed but settings could not be saved:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            self.refresh_status()
            return

        self._settings = data
        self._enabled_var.set(False)
        self._message_var.set("Removed.")
        logger.info("Schedule removed and scheduled_clean_enabled=False")
        if self._on_settings_updated is not None:
            self._on_settings_updated(dict(data))
        self.refresh_status()
