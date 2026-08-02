"""TempCleaner application entrypoint: CLI modes and GUI bootstrap."""

from __future__ import annotations

import argparse
import logging
import sys
from typing import Sequence

from tempcleaner.version import __version__

logger = logging.getLogger("tempcleaner.app")

# Exit codes
EXIT_OK = 0
EXIT_ERROR = 1
EXIT_USAGE = 2


def main(argv: list[str] | None = None) -> int:
    """Parse *argv* (default: ``sys.argv[1:]``) and run the requested mode.

    Returns:
        0 on success, 1 on error, 2 on bad usage.
    """
    args = _parse_args(argv if argv is not None else sys.argv[1:])

    if args.version:
        print(f"TempCleaner {__version__}")
        return EXIT_OK

    # --clean requires explicit --yes (non-interactive permanent delete)
    if args.clean and not args.yes:
        print(
            "error: --clean requires --yes to confirm permanent deletion",
            file=sys.stderr,
        )
        return EXIT_USAGE

    # Windows-only for GUI and operational modes (--version/--help already handled)
    if sys.platform != "win32":
        print(
            "TempCleaner supports Windows only. Refusing to start on this platform.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    try:
        from tempcleaner.util.logging_setup import setup_logging
        from tempcleaner.config.settings import SettingsStore

        settings_store = SettingsStore()
        settings = settings_store.load()
        log_level = str(settings.get("log_level", "INFO"))
        setup_logging(level=log_level)

        if args.scheduled:
            return _run_scheduled(settings)

        if args.scan or args.dry_run or args.clean:
            return _run_headless(args, settings)

        # Default: GUI
        return _run_gui_mode()
    except KeyboardInterrupt:
        print("Interrupted.", file=sys.stderr)
        return EXIT_ERROR
    except Exception:
        logger.exception("Unhandled error in application entrypoint")
        return EXIT_ERROR


def run_gui() -> None:
    """Open the TempCleaner GUI.

    Task 8: minimal Tk placeholder. Task 9 replaces this with the full ttk UI.
    """
    import tkinter as tk

    root = tk.Tk()
    root.title("TempCleaner")
    root.minsize(320, 160)
    label = tk.Label(
        root,
        text=f"TempCleaner {__version__}\nGUI coming in a later build.",
        justify="center",
        padx=40,
        pady=40,
    )
    label.pack(expand=True)
    root.mainloop()


def _parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="tempcleaner",
        description="TempCleaner - Windows temp and cache cleaner (v2).",
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="print version and exit",
    )

    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--scan",
        action="store_true",
        help="measure selected targets without deleting",
    )
    mode.add_argument(
        "--dry-run",
        action="store_true",
        help="simulate clean (same measurement path; no deletes)",
    )
    mode.add_argument(
        "--clean",
        action="store_true",
        help="permanently delete target contents (requires --yes)",
    )
    mode.add_argument(
        "--scheduled",
        action="store_true",
        help="headless scheduled clean (uses settings; trusted path)",
    )

    parser.add_argument(
        "--targets",
        metavar="id,id",
        default=None,
        help="comma-separated target ids (default: settings selected_targets)",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="confirm permanent delete for --clean",
    )

    # argparse may call sys.exit on --help / parse errors; that is intentional
    return parser.parse_args(list(argv))


def _run_gui_mode() -> int:
    logger.info("Starting GUI")
    run_gui()
    return EXIT_OK


def _run_headless(args: argparse.Namespace, settings: dict) -> int:
    from tempcleaner.core.engine import CleanEngine
    from tempcleaner.util.sizing import format_bytes

    target_ids = _resolve_cli_targets(settings, args.targets)
    if not target_ids:
        print("No targets selected.", file=sys.stderr)
        return EXIT_ERROR

    engine = CleanEngine()
    logger.info(
        "Headless mode action=%s targets=%s",
        "clean" if args.clean else ("dry_run" if args.dry_run else "scan"),
        target_ids,
    )

    if args.scan:
        report = engine.scan(target_ids)
    elif args.dry_run:
        report = engine.dry_run(target_ids)
    else:
        report = engine.clean(target_ids, confirmed=True)

    _print_report(report, format_bytes)
    if report.cancelled:
        logger.warning("Operation cancelled")
        return EXIT_ERROR
    return EXIT_OK


def _run_scheduled(settings: dict) -> int:
    """Trusted headless clean path for Task Scheduler.

    Confirmation is waived only here (and CLI --clean --yes); logs heavily.
    """
    from tempcleaner.core.engine import CleanEngine
    from tempcleaner.util.sizing import format_bytes

    enabled = bool(settings.get("scheduled_clean_enabled", False))
    logger.info(
        "Scheduled clean invoked: scheduled_clean_enabled=%s scheduled_targets=%s "
        "allow_advanced_targets=%s allow_prefetch_scheduled=%s",
        enabled,
        settings.get("scheduled_targets"),
        settings.get("allow_advanced_targets"),
        settings.get("allow_prefetch_scheduled"),
    )

    if not enabled:
        logger.info("Scheduled clean is disabled in settings; exiting without action")
        return EXIT_OK

    target_ids = _resolve_scheduled_targets(settings)
    if not target_ids:
        logger.warning("No scheduled targets after filtering; nothing to clean")
        return EXIT_OK

    logger.info("Starting scheduled permanent clean for targets: %s", target_ids)
    engine = CleanEngine()
    report = engine.clean(target_ids, confirmed=True)
    _print_report(report, format_bytes)
    logger.info(
        "Scheduled clean finished: action=%s cancelled=%s target_results=%d",
        report.action,
        report.cancelled,
        len(report.targets),
    )
    if report.cancelled:
        return EXIT_ERROR
    return EXIT_OK


def _resolve_cli_targets(settings: dict, targets_arg: str | None) -> list[str]:
    """Resolve target ids for --scan / --dry-run / --clean.

    Explicit ``--targets`` is honored as-is (power-user override).
    Otherwise use settings ``selected_targets``, then default-enabled ids.
    """
    if targets_arg is not None:
        return [part.strip() for part in targets_arg.split(",") if part.strip()]

    selected = settings.get("selected_targets")
    if isinstance(selected, list) and selected:
        return _filter_by_settings([str(x) for x in selected], settings, scheduled=False)

    from tempcleaner.core.targets import default_enabled_ids

    return default_enabled_ids()


def _resolve_scheduled_targets(settings: dict) -> list[str]:
    raw = settings.get("scheduled_targets") or []
    if not isinstance(raw, list):
        return []
    ids = [str(x) for x in raw if str(x).strip()]
    return _filter_by_settings(ids, settings, scheduled=True)


def _filter_by_settings(
    ids: list[str],
    settings: dict,
    *,
    scheduled: bool,
) -> list[str]:
    """Drop advanced/prefetch targets when settings forbid them."""
    from tempcleaner.core.models import RiskLevel
    from tempcleaner.core.targets import all_targets

    allow_advanced = bool(settings.get("allow_advanced_targets", False))
    allow_prefetch_scheduled = bool(settings.get("allow_prefetch_scheduled", False))
    registry = all_targets()
    out: list[str] = []
    for tid in ids:
        spec = registry.get(tid)
        if spec is None:
            logger.warning("Unknown target id skipped: %s", tid)
            continue
        if not allow_advanced and spec.risk == RiskLevel.ADVANCED:
            logger.info("Skipping advanced target (not allowed): %s", tid)
            continue
        if scheduled and tid == "prefetch" and not allow_prefetch_scheduled:
            logger.info("Skipping prefetch (allow_prefetch_scheduled=False): %s", tid)
            continue
        out.append(tid)
    return out


def _print_report(report, format_bytes) -> None:
    """Write a concise human-readable engine report to stdout and log."""
    print(f"Action: {report.action}")
    if report.cancelled:
        print("Status: cancelled")
    for stats in report.targets:
        bytes_str = format_bytes(stats.total_bytes)
        line = (
            f"  [{stats.target_id}] path={stats.path} "
            f"files={stats.file_count} dirs={stats.dir_count} size={bytes_str}"
        )
        deleted_files = getattr(stats, "deleted_files", None)
        if deleted_files is not None:
            line += (
                f" deleted_files={stats.deleted_files}"
                f" deleted_dirs={stats.deleted_dirs}"
                f" skipped={stats.skipped}"
                f" failed={stats.failed}"
                f" freed={format_bytes(stats.bytes_freed)}"
            )
        print(line)
        logger.info(line.strip())
        for err in stats.errors:
            print(f"    ! {err}", file=sys.stderr)
            logger.warning("[%s] %s", stats.target_id, err)


if __name__ == "__main__":
    raise SystemExit(main())
