"""Main ttk window: shell, Clean tab, worker thread, confirm gate."""

from __future__ import annotations

import logging
import threading
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Any

from tempcleaner.config.settings import SettingsStore
from tempcleaner.core.engine import CleanEngine, NotConfirmedError
from tempcleaner.core.models import CleanTargetSpec, EngineReport, RiskLevel
from tempcleaner.core.targets import all_targets, default_enabled_ids
from tempcleaner.platform_win.admin import is_admin, relaunch_as_admin
from tempcleaner.ui.components import AdminBadge, StatusBar, risk_tag_text
from tempcleaner.ui.dialogs import confirm_delete_dialog
from tempcleaner.ui.logs_view import LogsView
from tempcleaner.ui.results_view import ResultsView
from tempcleaner.ui.schedule_view import ScheduleView
from tempcleaner.ui.settings_view import SettingsView
from tempcleaner.util.sizing import format_bytes
from tempcleaner.version import __version__

logger = logging.getLogger("tempcleaner.ui.main_window")


def run_gui() -> None:
    """Build and run the TempCleaner main window (blocking mainloop)."""
    app = MainWindow()
    app.run()


class MainWindow:
    """Application shell with notebook tabs; Clean + Results + Settings + Logs wired."""

    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(f"TempCleaner {__version__}")
        self.root.minsize(720, 520)
        self.root.geometry("800x560")
        self._try_set_icon()

        self._settings_store = SettingsStore()
        self._settings: dict[str, Any] = self._settings_store.load()
        self._engine = CleanEngine()
        self._targets: dict[str, CleanTargetSpec] = all_targets()

        self._elevated = is_admin()
        self._busy = False
        self._cancel_event = threading.Event()
        self._worker: threading.Thread | None = None

        # Session dry-run gate: frozenset of target ids from last successful dry-run
        self.last_dry_run_signature: frozenset[str] | None = None
        # Optional size hint from last scan/dry-run for confirm dialog
        self._last_total_bytes: int | None = None
        self._last_report: EngineReport | None = None

        # target_id -> BooleanVar for checkboxes
        self._target_vars: dict[str, tk.BooleanVar] = {}
        self._target_checkbuttons: dict[str, ttk.Checkbutton] = {}

        self._build_shell()
        self._build_clean_tab()
        self._refresh_admin_ui()
        self._set_status("Ready")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # Optional quiet startup update check (setting default off)
        if bool(self._settings.get("check_updates_on_startup", False)):
            self.root.after(800, self._startup_update_check)

    def run(self) -> None:
        self.root.mainloop()

    def _try_set_icon(self) -> None:
        """Best-effort window icon from project maicon.ico if present."""
        from pathlib import Path

        candidates = [
            Path(__file__).resolve().parents[3] / "maicon.ico",
            Path(__file__).resolve().parents[2] / "maicon.ico",
        ]
        for path in candidates:
            if path.is_file():
                try:
                    self.root.iconbitmap(default=str(path))
                except tk.TclError:
                    try:
                        self.root.iconbitmap(str(path))
                    except tk.TclError:
                        pass
                return

    # ------------------------------------------------------------------ shell
    def _build_shell(self) -> None:
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(1, weight=1)

        # Top bar
        top = ttk.Frame(self.root, padding=(12, 10, 12, 6))
        top.grid(row=0, column=0, sticky="ew")
        top.columnconfigure(0, weight=1)

        title = ttk.Label(
            top,
            text=f"TempCleaner {__version__}",
            font=("", 12, "bold"),
        )
        title.grid(row=0, column=0, sticky="w")

        self._admin_badge = AdminBadge(
            top,
            is_elevated=self._elevated,
            on_relaunch=self._on_relaunch_as_admin,
        )
        self._admin_badge.grid(row=0, column=1, sticky="e")

        # Notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))

        self.clean_frame = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.clean_frame, text="Clean")

        self.results_view = ResultsView(self.notebook, padding=10)
        self.notebook.add(self.results_view, text="Results")

        self.schedule_view = ScheduleView(
            self.notebook,
            store=self._settings_store,
            settings=self._settings,
            get_selected_targets=self._selected_target_ids,
            on_settings_updated=self._on_schedule_settings_updated,
            padding=10,
        )
        self.notebook.add(self.schedule_view, text="Schedule")

        self.settings_view = SettingsView(
            self.notebook,
            store=self._settings_store,
            settings=self._settings,
            on_settings_saved=self._on_settings_saved,
            padding=10,
        )
        self.notebook.add(self.settings_view, text="Settings")

        self.logs_view = LogsView(self.notebook, padding=10)
        self.notebook.add(self.logs_view, text="Logs")

        # Status bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.grid(row=2, column=0, sticky="ew")

    # ---------------------------------------------------------------- Clean tab
    def _build_clean_tab(self) -> None:
        frame = self.clean_frame
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        # Header / helpers
        header = ttk.Frame(frame)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Select clean targets, then Scan, Dry-run, or Clean.",
        ).grid(row=0, column=0, sticky="w")

        helpers = ttk.Frame(header)
        helpers.grid(row=0, column=1, sticky="e")
        ttk.Button(
            helpers, text="Select all safe", command=self._select_all_safe
        ).grid(row=0, column=0, padx=(0, 6))
        ttk.Button(
            helpers, text="Select defaults", command=self._select_defaults
        ).grid(row=0, column=1)

        # Scrollable target list
        list_outer = ttk.LabelFrame(frame, text="Targets", padding=8)
        list_outer.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        list_outer.columnconfigure(0, weight=1)
        list_outer.rowconfigure(0, weight=1)

        canvas = tk.Canvas(list_outer, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(list_outer, orient="vertical", command=canvas.yview)
        self._targets_inner = ttk.Frame(canvas)
        self._targets_inner.bind(
            "<Configure>",
            lambda _e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        self._targets_window = canvas.create_window(
            (0, 0), window=self._targets_inner, anchor="nw"
        )
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfigure(self._targets_window, width=event.width)

        canvas.bind("<Configure>", _on_canvas_configure)

        self._populate_target_checkboxes()

        # Summary
        summary_box = ttk.LabelFrame(frame, text="Summary", padding=8)
        summary_box.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        summary_box.columnconfigure(0, weight=1)
        self._summary_var = tk.StringVar(value="No scan yet.")
        ttk.Label(
            summary_box,
            textvariable=self._summary_var,
            wraplength=720,
            justify="left",
        ).grid(row=0, column=0, sticky="w")

        # Progress
        prog_row = ttk.Frame(frame)
        prog_row.grid(row=3, column=0, sticky="ew", pady=(0, 8))
        prog_row.columnconfigure(0, weight=1)
        self._progress = ttk.Progressbar(
            prog_row, mode="indeterminate", length=200
        )
        self._progress.grid(row=0, column=0, sticky="ew", padx=(0, 8))
        self._progress_label = ttk.Label(prog_row, text="")
        self._progress_label.grid(row=0, column=1, sticky="e")

        # Actions
        actions = ttk.Frame(frame)
        actions.grid(row=4, column=0, sticky="ew")
        actions.columnconfigure(4, weight=1)

        self._scan_btn = ttk.Button(actions, text="Scan", command=self._on_scan)
        self._scan_btn.grid(row=0, column=0, padx=(0, 6))

        self._dry_run_btn = ttk.Button(
            actions, text="Dry-run", command=self._on_dry_run
        )
        self._dry_run_btn.grid(row=0, column=1, padx=(0, 6))

        self._clean_btn = ttk.Button(actions, text="Clean…", command=self._on_clean)
        self._clean_btn.grid(row=0, column=2, padx=(0, 6))

        self._cancel_btn = ttk.Button(
            actions, text="Cancel", command=self._on_cancel, state="disabled"
        )
        self._cancel_btn.grid(row=0, column=3, padx=(0, 6))

    def _populate_target_checkboxes(self) -> None:
        for child in self._targets_inner.winfo_children():
            child.destroy()
        self._target_vars.clear()
        self._target_checkbuttons.clear()

        allow_advanced = bool(self._settings.get("allow_advanced_targets", False))
        selected = self._settings.get("selected_targets")
        if not isinstance(selected, list) or not selected:
            selected = default_enabled_ids()
        selected_set = {str(x) for x in selected}

        row = 0
        for tid, spec in self._targets.items():
            if spec.risk is RiskLevel.ADVANCED and not allow_advanced:
                continue

            var = tk.BooleanVar(value=tid in selected_set)
            var.trace_add("write", self._on_selection_changed)
            self._target_vars[tid] = var

            risk = risk_tag_text(spec.risk)
            admin_note = " · admin" if spec.requires_admin else ""
            label = f"{spec.name}  [{risk}{admin_note}]"
            cb = ttk.Checkbutton(
                self._targets_inner,
                text=label,
                variable=var,
            )
            cb.grid(row=row, column=0, sticky="w", pady=2)
            self._target_checkbuttons[tid] = cb

            desc = ttk.Label(
                self._targets_inner,
                text=spec.description,
                foreground="gray",
            )
            desc.grid(row=row, column=1, sticky="w", padx=(12, 0), pady=2)
            row += 1

        if row == 0:
            ttk.Label(
                self._targets_inner,
                text="No targets available.",
            ).grid(row=0, column=0, sticky="w")

    def _on_selection_changed(self, *_args: object) -> None:
        # Changing selection invalidates the require-dry-run session gate
        current = self._selected_target_ids()
        if (
            self.last_dry_run_signature is not None
            and frozenset(current) != self.last_dry_run_signature
        ):
            self.last_dry_run_signature = None

    # ----------------------------------------------------------- target select
    def _selected_target_ids(self) -> list[str]:
        return [tid for tid, var in self._target_vars.items() if var.get()]

    def _select_all_safe(self) -> None:
        for tid, var in self._target_vars.items():
            spec = self._targets[tid]
            var.set(spec.risk is RiskLevel.SAFE)

    def _select_defaults(self) -> None:
        defaults = set(default_enabled_ids())
        for tid, var in self._target_vars.items():
            var.set(tid in defaults)

    # ----------------------------------------------------------------- admin UI
    def _refresh_admin_ui(self) -> None:
        self._elevated = is_admin()
        self._admin_badge.set_elevated(self._elevated)

    def _on_relaunch_as_admin(self) -> None:
        if self._busy:
            messagebox.showinfo(
                "Busy",
                "Wait for the current operation to finish before restarting.",
                parent=self.root,
            )
            return
        try:
            relaunch_as_admin()
        except OSError as exc:
            logger.warning("Relaunch as admin failed: %s", exc)
            messagebox.showerror(
                "Elevation failed",
                f"Could not restart as administrator.\n\n{exc}",
                parent=self.root,
            )
            return
        # Elevated process started; exit this instance
        self.root.destroy()

    # --------------------------------------------------------------- operations
    def _on_scan(self) -> None:
        ids = self._selected_target_ids()
        if not ids:
            messagebox.showinfo(
                "No targets",
                "Select at least one target to scan.",
                parent=self.root,
            )
            return
        if not self._check_admin_for_selection(ids):
            return
        self._start_worker("scan", ids)

    def _on_dry_run(self) -> None:
        ids = self._selected_target_ids()
        if not ids:
            messagebox.showinfo(
                "No targets",
                "Select at least one target for dry-run.",
                parent=self.root,
            )
            return
        if not self._check_admin_for_selection(ids):
            return
        self._start_worker("dry_run", ids)

    def _on_clean(self) -> None:
        ids = self._selected_target_ids()
        if not ids:
            messagebox.showinfo(
                "No targets",
                "Select at least one target to clean.",
                parent=self.root,
            )
            return
        if not self._check_admin_for_selection(ids):
            return

        require_dry = bool(self._settings.get("require_dry_run_before_clean", True))
        sig = frozenset(ids)
        if require_dry and self.last_dry_run_signature != sig:
            messagebox.showwarning(
                "Dry-run required",
                "A dry-run for the current target selection is required before "
                "cleaning.\n\nRun Dry-run first, or disable this requirement in "
                "the Settings tab (Require dry-run before clean).",
                parent=self.root,
            )
            self._set_status("Clean blocked: dry-run required for current selection")
            return

        names = [self._targets[i].name for i in ids if i in self._targets]
        if not confirm_delete_dialog(
            self.root,
            target_names=names,
            total_bytes=self._last_total_bytes,
        ):
            self._set_status("Clean cancelled (confirm dialog)")
            return

        self._start_worker("clean", ids)

    def _on_cancel(self) -> None:
        if self._busy:
            self._cancel_event.set()
            self._set_status("Cancelling…")
            self._progress_label.configure(text="Cancelling…")

    def _check_admin_for_selection(self, ids: list[str]) -> bool:
        """If selection needs admin and we are not elevated, offer relaunch."""
        needs_admin = any(
            self._targets[i].requires_admin for i in ids if i in self._targets
        )
        if not needs_admin or self._elevated:
            return True
        names = [
            self._targets[i].name
            for i in ids
            if i in self._targets and self._targets[i].requires_admin
        ]
        msg = (
            "Some selected targets usually require administrator rights:\n\n"
            f"  {', '.join(names)}\n\n"
            "Restart as admin, or continue as a standard user "
            "(permission errors may be skipped)?"
        )
        choice = messagebox.askyesnocancel(
            "Administrator recommended",
            msg + "\n\nYes = Restart as admin\nNo = Continue\nCancel = Abort",
            parent=self.root,
        )
        if choice is None:
            return False
        if choice:
            self._on_relaunch_as_admin()
            return False
        return True

    def _start_worker(self, action: str, target_ids: list[str]) -> None:
        if self._busy:
            return
        self._busy = True
        self._cancel_event = threading.Event()
        self._set_action_buttons_enabled(False)
        self._cancel_btn.state(["!disabled"])
        self._progress.start(12)
        self._progress_label.configure(text=f"{action}…")
        self._set_status(f"Running {action}…")
        logger.info("UI start action=%s targets=%s", action, target_ids)

        def work() -> None:
            report: EngineReport | None = None
            error: BaseException | None = None
            try:
                if action == "scan":
                    report = self._engine.scan(
                        target_ids, cancel_event=self._cancel_event
                    )
                elif action == "dry_run":
                    report = self._engine.dry_run(
                        target_ids, cancel_event=self._cancel_event
                    )
                elif action == "clean":
                    report = self._engine.clean(
                        target_ids,
                        confirmed=True,
                        cancel_event=self._cancel_event,
                    )
                else:
                    raise ValueError(f"Unknown action: {action}")
            except NotConfirmedError as exc:
                error = exc
            except OSError as exc:
                error = exc
            except Exception as exc:  # noqa: BLE001 — surface unexpected to UI
                logger.exception("Worker failed action=%s", action)
                error = exc

            self.root.after(
                0,
                lambda: self._on_worker_done(action, target_ids, report, error),
            )

        self._worker = threading.Thread(target=work, name=f"tc-{action}", daemon=True)
        self._worker.start()

    def _on_worker_done(
        self,
        action: str,
        target_ids: list[str],
        report: EngineReport | None,
        error: BaseException | None,
    ) -> None:
        self._busy = False
        self._progress.stop()
        self._progress_label.configure(text="")
        self._set_action_buttons_enabled(True)
        self._cancel_btn.state(["disabled"])

        if error is not None:
            self._set_status(f"{action} failed: {error}")
            messagebox.showerror(
                "Operation failed",
                f"{action} failed:\n\n{error}",
                parent=self.root,
            )
            return

        assert report is not None
        self._last_report = report
        total_bytes = sum(t.total_bytes for t in report.targets)
        self._last_total_bytes = total_bytes
        self._update_summary(report)
        self._populate_results(report)

        if action == "dry_run" and not report.cancelled:
            self.last_dry_run_signature = frozenset(target_ids)
            # Design: dry-run auto-switches to Results
            try:
                self.notebook.select(self.results_view)
            except tk.TclError:
                pass

        if report.cancelled:
            self._set_status(f"{action} cancelled")
        else:
            freed = 0
            for t in report.targets:
                freed += getattr(t, "bytes_freed", 0) or 0
            if action == "clean":
                self._set_status(
                    f"Clean finished — freed {format_bytes(freed)} "
                    f"({len(report.targets)} result rows)"
                )
            else:
                self._set_status(
                    f"{action} finished — {format_bytes(total_bytes)} found "
                    f"({len(report.targets)} result rows)"
                )
        logger.info(
            "UI done action=%s cancelled=%s rows=%d total_bytes=%s",
            action,
            report.cancelled,
            len(report.targets),
            total_bytes,
        )

    def _update_summary(self, report: EngineReport) -> None:
        lines: list[str] = [f"Action: {report.action}"]
        if report.cancelled:
            lines.append("Status: cancelled")
        total_files = 0
        total_dirs = 0
        total_bytes = 0
        for stats in report.targets:
            total_files += stats.file_count
            total_dirs += stats.dir_count
            total_bytes += stats.total_bytes
            err_n = len(stats.errors)
            extra = ""
            if hasattr(stats, "deleted_files"):
                extra = (
                    f" | deleted_files={stats.deleted_files}"
                    f" deleted_dirs={stats.deleted_dirs}"
                    f" skipped={stats.skipped}"
                    f" failed={stats.failed}"
                    f" freed={format_bytes(stats.bytes_freed)}"
                )
            lines.append(
                f"• {stats.target_id}: files={stats.file_count} "
                f"dirs={stats.dir_count} size={format_bytes(stats.total_bytes)}"
                f"{extra}"
                + (f" ({err_n} messages)" if err_n else "")
            )
        lines.append(
            f"Totals: files={total_files} dirs={total_dirs} "
            f"size={format_bytes(total_bytes)}"
        )
        self._summary_var.set("\n".join(lines))

    def _populate_results(self, report: EngineReport) -> None:
        """Push the engine report into the Results tab."""
        names = {tid: spec.name for tid, spec in self._targets.items()}
        self.results_view.set_report(report, target_names=names)

    def _on_settings_saved(self, settings: dict[str, Any]) -> None:
        """Apply settings from the Settings tab to live MainWindow state."""
        previous_selected = self._selected_target_ids()
        self._settings = dict(settings)
        # Keep Clean-tab checks when rebuilding visibility (advanced on/off)
        if previous_selected:
            self._settings["selected_targets"] = list(previous_selected)
        self._populate_target_checkboxes()
        # Keep Schedule tab widgets in sync (non-schedule keys may have changed)
        self.schedule_view.load_from_settings(self._settings)
        self.schedule_view.refresh_status()
        self._set_status("Settings saved")
        logger.info(
            "Settings applied: require_dry_run=%s allow_advanced=%s close_minimizes=%s",
            settings.get("require_dry_run_before_clean"),
            settings.get("allow_advanced_targets"),
            settings.get("close_minimizes"),
        )

    def _on_schedule_settings_updated(self, settings: dict[str, Any]) -> None:
        """Apply schedule-related settings saved from the Schedule tab."""
        previous_selected = self._selected_target_ids()
        self._settings = dict(settings)
        if previous_selected:
            self._settings["selected_targets"] = list(previous_selected)
        # Settings tab keeps its own copy of schedule-related keys
        self.settings_view.load_from_settings(self._settings)
        enabled = bool(settings.get("scheduled_clean_enabled", False))
        self._set_status(
            "Schedule applied"
            if enabled
            else "Schedule disabled / removed"
        )
        logger.info(
            "Schedule settings updated: enabled=%s targets=%s freq=%s time=%s",
            settings.get("scheduled_clean_enabled"),
            settings.get("scheduled_targets"),
            settings.get("schedule_frequency"),
            settings.get("schedule_time"),
        )

    def _on_tab_changed(self, _event: object = None) -> None:
        """Refresh Logs / Schedule status when those tabs are selected."""
        try:
            current = self.notebook.select()
        except tk.TclError:
            return
        if not current:
            return
        try:
            widget = self.notebook.nametowidget(current)
            if str(widget) == str(self.logs_view):
                self.logs_view.refresh()
            elif str(widget) == str(self.schedule_view):
                self.schedule_view.refresh_status()
        except tk.TclError:
            pass

    def _set_action_buttons_enabled(self, enabled: bool) -> None:
        state = ["!disabled"] if enabled else ["disabled"]
        self._scan_btn.state(state)
        self._dry_run_btn.state(state)
        self._clean_btn.state(state)

    def _set_status(self, text: str) -> None:
        self.status_bar.set_text(text)

    def _startup_update_check(self) -> None:
        """Background update check when check_updates_on_startup is enabled.

        Only prompts when a newer release is found; failures are silent
        (logged) so startup is never blocked.
        """
        import webbrowser

        from tempcleaner.platform_win.updates import check_latest_release

        def work() -> None:
            available, latest_tag, html_url = check_latest_release(__version__)
            if not available or latest_tag is None:
                return

            def notify() -> None:
                msg = (
                    f"A newer TempCleaner release is available.\n\n"
                    f"Current: {__version__}\n"
                    f"Latest:  {latest_tag}\n"
                )
                if html_url:
                    msg += f"\nOpen release page?\n{html_url}"
                    if messagebox.askyesno(
                        "Update available", msg, parent=self.root
                    ):
                        try:
                            webbrowser.open(html_url)
                        except OSError as exc:
                            logger.warning("Could not open browser: %s", exc)
                else:
                    messagebox.showinfo(
                        "Update available", msg, parent=self.root
                    )
                self._set_status(f"Update available: {latest_tag}")

            try:
                self.root.after(0, notify)
            except tk.TclError:
                pass

        threading.Thread(
            target=work, name="tc-startup-update", daemon=True
        ).start()

    def _persist_selected_targets(self) -> None:
        """Write current checkbox selection into settings (best-effort)."""
        selected = self._selected_target_ids()
        if not selected:
            return
        data = dict(self._settings)
        data["selected_targets"] = selected
        try:
            self._settings_store.save(data)
            self._settings = data
        except OSError as exc:
            logger.warning("Could not persist selected_targets: %s", exc)

    def _on_close(self) -> None:
        if self._busy:
            if not messagebox.askyesno(
                "Operation in progress",
                "An operation is still running. Cancel and exit?",
                parent=self.root,
            ):
                return
            self._cancel_event.set()

        self._persist_selected_targets()

        if bool(self._settings.get("close_minimizes", False)):
            self.root.iconify()
            return

        self.root.destroy()
