"""Logs tab: tail of current log file, refresh, open folder."""

from __future__ import annotations

import logging
import os
import subprocess
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import messagebox, ttk

from tempcleaner.platform_win.paths import appdata_dir

logger = logging.getLogger("tempcleaner.ui.logs_view")

_DEFAULT_TAIL_LINES = 200


def current_log_path(log_dir: Path | None = None) -> Path:
    """Return the expected path for today's TempCleaner log file."""
    if log_dir is None:
        log_dir = appdata_dir() / "logs"
    date_str = datetime.now().strftime("%Y%m%d")
    return Path(log_dir) / f"tempcleaner-{date_str}.log"


def read_log_tail(path: Path, max_lines: int = _DEFAULT_TAIL_LINES) -> str:
    """Read the last *max_lines* lines from *path* (UTF-8, best-effort).

    Returns a short status message if the file is missing or unreadable.
    """
    if max_lines < 1:
        max_lines = 1
    if not path.is_file():
        return f"(log file not found: {path})"
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return f"(could not read log: {exc})"
    if not text:
        return "(log file is empty)"
    lines = text.splitlines()
    if len(lines) > max_lines:
        tail = lines[-max_lines:]
        omitted = len(lines) - max_lines
        return f"… ({omitted} earlier lines omitted)\n" + "\n".join(tail)
    return "\n".join(lines)


class LogsView(ttk.Frame):
    """Show a live-refreshable tail of the current application log."""

    def __init__(
        self,
        parent: tk.Misc,
        *,
        log_path: Path | None = None,
        tail_lines: int = _DEFAULT_TAIL_LINES,
        **kwargs: object,
    ) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        self._log_path = log_path if log_path is not None else current_log_path()
        self._tail_lines = tail_lines
        self._path_var = tk.StringVar(value=str(self._log_path))
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(1, weight=1)

        ttk.Label(header, text="Log file:").grid(row=0, column=0, sticky="w")
        ttk.Label(header, textvariable=self._path_var).grid(
            row=0, column=1, sticky="w", padx=(6, 8)
        )

        btns = ttk.Frame(header)
        btns.grid(row=0, column=2, sticky="e")
        ttk.Button(btns, text="Refresh", command=self.refresh).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(btns, text="Open folder", command=self._open_folder).grid(
            row=0, column=1
        )

        text_frame = ttk.Frame(self)
        text_frame.grid(row=1, column=0, sticky="nsew")
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)

        self._text = tk.Text(
            text_frame,
            wrap="none",
            state="disabled",
            font=("Consolas", 9),
        )
        yscroll = ttk.Scrollbar(
            text_frame, orient="vertical", command=self._text.yview
        )
        xscroll = ttk.Scrollbar(
            text_frame, orient="horizontal", command=self._text.xview
        )
        self._text.configure(
            yscrollcommand=yscroll.set,
            xscrollcommand=xscroll.set,
        )
        self._text.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")
        xscroll.grid(row=1, column=0, sticky="ew")

        hint = ttk.Label(
            self,
            text=f"Showing last ~{self._tail_lines} lines. Use Refresh after operations.",
            foreground="gray",
        )
        hint.grid(row=2, column=0, sticky="w", pady=(6, 0))

    def set_log_path(self, path: Path) -> None:
        """Point the viewer at a different log file and refresh."""
        self._log_path = Path(path)
        self._path_var.set(str(self._log_path))
        self.refresh()

    def refresh(self) -> None:
        """Reload the tail of the current log into the text widget."""
        # Re-resolve today's path if caller used default (date rollover)
        if self._log_path.name.startswith("tempcleaner-"):
            expected = current_log_path(self._log_path.parent)
            if expected != self._log_path:
                self._log_path = expected
                self._path_var.set(str(self._log_path))

        content = read_log_tail(self._log_path, self._tail_lines)
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.insert("1.0", content)
        self._text.configure(state="disabled")
        # Scroll to end
        self._text.see("end")
        logger.debug("Logs view refreshed from %s", self._log_path)

    def _open_folder(self) -> None:
        folder = self._log_path.parent
        try:
            folder.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            messagebox.showerror(
                "Open folder failed",
                f"Could not create logs folder:\n{folder}\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        try:
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except OSError:
            try:
                subprocess.run(
                    ["explorer", str(folder)],
                    check=False,
                    capture_output=True,
                )
            except OSError as exc:
                messagebox.showerror(
                    "Open folder failed",
                    f"Could not open:\n{folder}\n\n{exc}",
                    parent=self.winfo_toplevel(),
                )
