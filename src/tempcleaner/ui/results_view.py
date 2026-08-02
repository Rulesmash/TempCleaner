"""Results tab: per-target engine report table and export."""

from __future__ import annotations

import json
import tkinter as tk
from collections.abc import Mapping
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tempcleaner.core.models import EngineReport, TargetCleanStats, TargetScanStats
from tempcleaner.util.sizing import format_bytes


class ResultsView(ttk.Frame):
    """Tree of last engine report rows with optional error samples and export."""

    COLUMNS = (
        "target",
        "action",
        "found",
        "deleted",
        "skipped",
        "failed",
        "bytes",
    )

    def __init__(self, parent: tk.Misc, **kwargs: object) -> None:
        super().__init__(parent, **kwargs)  # type: ignore[arg-type]
        self._report: EngineReport | None = None
        self._target_names: dict[str, str] = {}
        self._build()

    def _build(self) -> None:
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)
        self.rowconfigure(3, weight=1)

        header = ttk.Frame(self)
        header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        header.columnconfigure(0, weight=1)

        ttk.Label(
            header,
            text="Last scan / dry-run / clean results.",
        ).grid(row=0, column=0, sticky="w")

        btns = ttk.Frame(header)
        btns.grid(row=0, column=1, sticky="e")
        ttk.Button(btns, text="Export JSON…", command=self._export_json).grid(
            row=0, column=0, padx=(0, 6)
        )
        ttk.Button(btns, text="Export TXT…", command=self._export_txt).grid(
            row=0, column=1
        )

        table_frame = ttk.LabelFrame(self, text="Results", padding=6)
        table_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 8))
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            table_frame,
            columns=self.COLUMNS,
            show="headings",
            selectmode="browse",
        )
        headings = {
            "target": "Target",
            "action": "Action",
            "found": "Found",
            "deleted": "Deleted",
            "skipped": "Skipped",
            "failed": "Failed",
            "bytes": "Bytes",
        }
        widths = {
            "target": 160,
            "action": 80,
            "found": 70,
            "deleted": 70,
            "skipped": 70,
            "failed": 70,
            "bytes": 100,
        }
        for col in self.COLUMNS:
            self._tree.heading(col, text=headings[col])
            self._tree.column(col, width=widths[col], minwidth=50, anchor="w")

        yscroll = ttk.Scrollbar(
            table_frame, orient="vertical", command=self._tree.yview
        )
        self._tree.configure(yscrollcommand=yscroll.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        yscroll.grid(row=0, column=1, sticky="ns")

        self._meta_var = tk.StringVar(value="No results yet. Run Scan, Dry-run, or Clean.")
        ttk.Label(self, textvariable=self._meta_var, wraplength=720).grid(
            row=2, column=0, sticky="w", pady=(0, 6)
        )

        err_frame = ttk.LabelFrame(self, text="Error samples", padding=6)
        err_frame.grid(row=3, column=0, sticky="nsew")
        err_frame.columnconfigure(0, weight=1)
        err_frame.rowconfigure(0, weight=1)

        self._errors = tk.Text(
            err_frame,
            height=6,
            wrap="word",
            state="disabled",
            font=("Consolas", 9),
        )
        err_scroll = ttk.Scrollbar(
            err_frame, orient="vertical", command=self._errors.yview
        )
        self._errors.configure(yscrollcommand=err_scroll.set)
        self._errors.grid(row=0, column=0, sticky="nsew")
        err_scroll.grid(row=0, column=1, sticky="ns")

    def clear(self) -> None:
        """Remove all rows and clear the stored report."""
        self._report = None
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._set_errors_text("")
        self._meta_var.set("No results yet. Run Scan, Dry-run, or Clean.")

    def set_report(
        self,
        report: EngineReport,
        *,
        target_names: Mapping[str, str] | None = None,
    ) -> None:
        """Populate the table from an :class:`EngineReport`."""
        self._report = report
        if target_names is not None:
            self._target_names = dict(target_names)

        for item in self._tree.get_children():
            self._tree.delete(item)

        error_lines: list[str] = []
        for stats in report.targets:
            self._tree.insert("", "end", values=self._row_values(report.action, stats))
            for err in stats.errors[:5]:
                error_lines.append(f"[{stats.target_id}] {err}")
            if len(stats.errors) > 5:
                extra = len(stats.errors) - 5
                error_lines.append(
                    f"[{stats.target_id}] … and {extra} more message(s)"
                )

        status = "cancelled" if report.cancelled else "ok"
        self._meta_var.set(
            f"Action: {report.action}  |  status: {status}  |  "
            f"rows: {len(report.targets)}"
        )
        self._set_errors_text(
            "\n".join(error_lines) if error_lines else "(no errors reported)"
        )

    def _row_values(
        self, action: str, stats: TargetScanStats | TargetCleanStats
    ) -> tuple[str, str, str, str, str, str, str]:
        name = self._target_names.get(stats.target_id, stats.target_id)
        found = str(stats.file_count)
        if isinstance(stats, TargetCleanStats):
            deleted = str(stats.deleted_files)
            skipped = str(stats.skipped)
            failed = str(stats.failed)
            # Prefer freed for clean; fall back to measured size
            bytes_col = format_bytes(
                stats.bytes_freed if action == "clean" else stats.total_bytes
            )
        else:
            deleted = "—"
            skipped = "—"
            failed = "—"
            bytes_col = format_bytes(stats.total_bytes)
        return (name, action, found, deleted, skipped, failed, bytes_col)

    def _set_errors_text(self, text: str) -> None:
        self._errors.configure(state="normal")
        self._errors.delete("1.0", "end")
        self._errors.insert("1.0", text)
        self._errors.configure(state="disabled")

    def _ensure_report(self) -> EngineReport | None:
        if self._report is None:
            messagebox.showinfo(
                "No results",
                "There is no report to export yet. Run Scan, Dry-run, or Clean first.",
                parent=self.winfo_toplevel(),
            )
            return None
        return self._report

    def _export_json(self) -> None:
        report = self._ensure_report()
        if report is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export results as JSON",
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            payload = self._report_to_dict(report)
            Path(path).write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        except OSError as exc:
            messagebox.showerror(
                "Export failed",
                f"Could not write JSON report:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        messagebox.showinfo(
            "Export complete",
            f"Wrote JSON report to:\n{path}",
            parent=self.winfo_toplevel(),
        )

    def _export_txt(self) -> None:
        report = self._ensure_report()
        if report is None:
            return
        path = filedialog.asksaveasfilename(
            parent=self.winfo_toplevel(),
            title="Export results as text",
            defaultextension=".txt",
            filetypes=[("Text", "*.txt"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            Path(path).write_text(self._report_to_text(report), encoding="utf-8")
        except OSError as exc:
            messagebox.showerror(
                "Export failed",
                f"Could not write text report:\n\n{exc}",
                parent=self.winfo_toplevel(),
            )
            return
        messagebox.showinfo(
            "Export complete",
            f"Wrote text report to:\n{path}",
            parent=self.winfo_toplevel(),
        )

    def _report_to_dict(self, report: EngineReport) -> dict:
        targets: list[dict] = []
        for stats in report.targets:
            row: dict = {
                "target_id": stats.target_id,
                "target_name": self._target_names.get(stats.target_id, stats.target_id),
                "path": str(stats.path),
                "file_count": stats.file_count,
                "dir_count": stats.dir_count,
                "total_bytes": stats.total_bytes,
                "errors": list(stats.errors),
            }
            if isinstance(stats, TargetCleanStats):
                row.update(
                    {
                        "deleted_files": stats.deleted_files,
                        "deleted_dirs": stats.deleted_dirs,
                        "skipped": stats.skipped,
                        "failed": stats.failed,
                        "bytes_freed": stats.bytes_freed,
                    }
                )
            targets.append(row)
        return {
            "action": report.action,
            "cancelled": report.cancelled,
            "targets": targets,
        }

    def _report_to_text(self, report: EngineReport) -> str:
        lines: list[str] = [
            f"TempCleaner report — action={report.action}",
            f"cancelled={report.cancelled}",
            "",
        ]
        for stats in report.targets:
            name = self._target_names.get(stats.target_id, stats.target_id)
            lines.append(f"Target: {name} ({stats.target_id})")
            lines.append(f"  path: {stats.path}")
            lines.append(
                f"  found files={stats.file_count} dirs={stats.dir_count} "
                f"size={format_bytes(stats.total_bytes)}"
            )
            if isinstance(stats, TargetCleanStats):
                lines.append(
                    f"  deleted_files={stats.deleted_files} "
                    f"deleted_dirs={stats.deleted_dirs} "
                    f"skipped={stats.skipped} failed={stats.failed} "
                    f"freed={format_bytes(stats.bytes_freed)}"
                )
            for err in stats.errors:
                lines.append(f"  ! {err}")
            lines.append("")
        return "\n".join(lines)
