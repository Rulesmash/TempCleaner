"""Modal dialogs for TempCleaner GUI."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable, Sequence
from tkinter import ttk

from tempcleaner.util.sizing import format_bytes
from tempcleaner.version import __version__


def about_dialog(
    parent: tk.Misc,
    *,
    on_check_updates: Callable[[], None] | None = None,
) -> None:
    """Show a simple About dialog (version, license note, optional update check)."""
    dialog = tk.Toplevel(parent)
    dialog.title("About TempCleaner")
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    try:
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        dw, dh = 400, 220
        x = px + max(0, (pw - dw) // 2)
        y = py + max(0, (ph - dh) // 2)
        dialog.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass

    frame = ttk.Frame(dialog, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(0, weight=1)

    ttk.Label(
        frame,
        text=f"TempCleaner {__version__}",
        font=("", 12, "bold"),
    ).grid(row=0, column=0, sticky="w", pady=(0, 8))

    ttk.Label(
        frame,
        text=(
            "Windows temp and cache cleaner with dry-run, confirmations, "
            "and scheduling.\n\n"
            "Deletes are permanent (not Recycle Bin).\n"
            "License: GNU GPLv3"
        ),
        wraplength=360,
        justify="left",
    ).grid(row=1, column=0, sticky="w", pady=(0, 12))

    btn_row = ttk.Frame(frame)
    btn_row.grid(row=2, column=0, sticky="e")

    def on_close() -> None:
        dialog.destroy()

    if on_check_updates is not None:

        def _check() -> None:
            dialog.destroy()
            on_check_updates()

        ttk.Button(btn_row, text="Check for updates", command=_check).grid(
            row=0, column=0, padx=(0, 8)
        )

    close_btn = ttk.Button(btn_row, text="Close", command=on_close)
    close_btn.grid(row=0, column=1)
    close_btn.focus_set()
    dialog.protocol("WM_DELETE_WINDOW", on_close)
    dialog.bind("<Escape>", lambda _e: on_close())
    parent.wait_window(dialog)


def confirm_delete_dialog(
    parent: tk.Misc,
    target_names: Sequence[str],
    total_bytes: int | None = None,
) -> bool:
    """Show permanent-delete confirmation.

    Displays target names, optional total size, and a permanent-delete warning.
    Delete is disabled until the user checks the acknowledgment box.
    Cancel is the default action (Enter must not trigger delete by default).

    Returns:
        True if the user confirmed delete; False if cancelled.
    """
    result = {"confirmed": False}

    dialog = tk.Toplevel(parent)
    dialog.title("Confirm permanent delete")
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    # Center over parent when possible
    try:
        parent.update_idletasks()
        px = parent.winfo_rootx()
        py = parent.winfo_rooty()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        dialog.update_idletasks()
        # Approximate size before pack finishes; place roughly centered
        dw, dh = 420, 280
        x = px + max(0, (pw - dw) // 2)
        y = py + max(0, (ph - dh) // 2)
        dialog.geometry(f"+{x}+{y}")
    except tk.TclError:
        pass

    frame = ttk.Frame(dialog, padding=16)
    frame.grid(row=0, column=0, sticky="nsew")
    dialog.columnconfigure(0, weight=1)
    dialog.rowconfigure(0, weight=1)

    ttk.Label(
        frame,
        text="You are about to permanently delete files.",
        font=("", 10, "bold"),
    ).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 8))

    warning = (
        "This action cannot be undone. Files will not be moved to the Recycle Bin."
    )
    ttk.Label(frame, text=warning, wraplength=380).grid(
        row=1, column=0, columnspan=2, sticky="w", pady=(0, 10)
    )

    names = ", ".join(target_names) if target_names else "(none)"
    ttk.Label(frame, text=f"Targets: {names}", wraplength=380).grid(
        row=2, column=0, columnspan=2, sticky="w", pady=(0, 4)
    )

    if total_bytes is not None:
        size_text = f"Estimated size: {format_bytes(total_bytes)}"
        ttk.Label(frame, text=size_text).grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )
    else:
        ttk.Label(frame, text="Estimated size: unknown (run Scan or Dry-run first)").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 10)
        )

    ack_var = tk.BooleanVar(value=False)
    ack = ttk.Checkbutton(
        frame,
        text="I understand files will be permanently deleted.",
        variable=ack_var,
    )
    ack.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 14))

    btn_row = ttk.Frame(frame)
    btn_row.grid(row=5, column=0, columnspan=2, sticky="e")

    def on_cancel() -> None:
        result["confirmed"] = False
        dialog.destroy()

    def on_delete() -> None:
        if not ack_var.get():
            return
        result["confirmed"] = True
        dialog.destroy()

    cancel_btn = ttk.Button(btn_row, text="Cancel", command=on_cancel)
    cancel_btn.grid(row=0, column=0, padx=(0, 8))

    delete_btn = ttk.Button(btn_row, text="Delete permanently", command=on_delete)
    delete_btn.grid(row=0, column=1)
    delete_btn.state(["disabled"])

    def _sync_delete_state(*_args: object) -> None:
        if ack_var.get():
            delete_btn.state(["!disabled"])
        else:
            delete_btn.state(["disabled"])

    ack_var.trace_add("write", _sync_delete_state)

    dialog.protocol("WM_DELETE_WINDOW", on_cancel)
    # Default focus / Enter binding stays on Cancel (not Delete)
    cancel_btn.focus_set()
    dialog.bind("<Escape>", lambda _e: on_cancel())
    dialog.bind("<Return>", lambda _e: on_cancel())

    parent.wait_window(dialog)
    return bool(result["confirmed"])
