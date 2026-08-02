"""Windows Task Scheduler integration via ``schtasks`` CLI.

Pure argv builders are unit-tested; install/remove/exists shell out to
``schtasks`` with ``capture_output=True, text=True, check=False`` and raise
``RuntimeError`` (including stderr) on non-zero exit.
"""

from __future__ import annotations

import logging
import re
import subprocess
import sys
from collections.abc import Sequence

logger = logging.getLogger("tempcleaner.platform_win.scheduler")

TASK_NAME = "TempCleaner Scheduled Clean"

# Hide console flash when spawning schtasks from a windowed GUI process.
_CREATE_NO_WINDOW = 0x08000000

_VALID_FREQUENCIES = frozenset({"daily", "weekly"})
_VALID_WEEKDAYS = frozenset(
    {"MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"}
)
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def build_scheduled_command() -> str:
    """Return the command line the scheduled task should run.

    Frozen (PyInstaller) EXE: ``"<exe>" --scheduled``.
    Interpreter: ``"<python>" -m tempcleaner --scheduled``.
    """
    exe = sys.executable
    if getattr(sys, "frozen", False):
        return subprocess.list2cmdline([exe, "--scheduled"])
    return subprocess.list2cmdline([exe, "-m", "tempcleaner", "--scheduled"])


def build_schtasks_create_args(
    *,
    task_name: str,
    frequency: str,
    time_hhmm: str,
    weekday: str | None,
    command: str,
) -> list[str]:
    """Build full argv for ``schtasks /Create`` (pure; no subprocess).

    Args:
        task_name: Task Scheduler task name (``/TN``).
        frequency: ``daily`` or ``weekly`` (case-insensitive).
        time_hhmm: 24-hour ``HH:MM``.
        weekday: Required for weekly (``MON``…``SUN``); ignored for daily.
        command: Full ``/TR`` task-run command string.

    Returns:
        Argv list starting with ``schtasks``.

    Raises:
        ValueError: Invalid frequency, time, weekday, or empty command.
    """
    if not task_name or not str(task_name).strip():
        raise ValueError("task_name must be non-empty")
    freq = str(frequency).strip().lower()
    if freq not in _VALID_FREQUENCIES:
        raise ValueError(
            f"frequency must be one of {sorted(_VALID_FREQUENCIES)}, got {frequency!r}"
        )
    time_s = str(time_hhmm).strip()
    if not _TIME_RE.match(time_s):
        raise ValueError(
            f"time must be HH:MM (24-hour), got {time_hhmm!r}"
        )
    cmd = str(command).strip()
    if not cmd:
        raise ValueError("command must be non-empty")

    args: list[str] = [
        "schtasks",
        "/Create",
        "/TN",
        str(task_name).strip(),
        "/TR",
        cmd,
        "/SC",
        freq.upper(),
        "/ST",
        time_s,
        "/F",
    ]

    if freq == "weekly":
        if weekday is None or not str(weekday).strip():
            raise ValueError("weekday is required for weekly frequency")
        day = str(weekday).strip().upper()
        if day not in _VALID_WEEKDAYS:
            raise ValueError(
                f"weekday must be one of {sorted(_VALID_WEEKDAYS)}, got {weekday!r}"
            )
        args.extend(["/D", day])

    return args


def build_schtasks_delete_args(task_name: str = TASK_NAME) -> list[str]:
    """Build argv for ``schtasks /Delete /TN … /F``."""
    return ["schtasks", "/Delete", "/TN", task_name, "/F"]


def build_schtasks_query_args(task_name: str = TASK_NAME) -> list[str]:
    """Build argv for ``schtasks /Query /TN …``."""
    return ["schtasks", "/Query", "/TN", task_name]


def install_schedule(
    frequency: str,
    time_hhmm: str,
    weekday: str | None,
    command: str,
) -> None:
    """Create or replace the TempCleaner scheduled task.

    Raises:
        RuntimeError: If ``schtasks`` returns non-zero (stderr included).
        ValueError: If schedule parameters are invalid.
    """
    args = build_schtasks_create_args(
        task_name=TASK_NAME,
        frequency=frequency,
        time_hhmm=time_hhmm,
        weekday=weekday,
        command=command,
    )
    _run_schtasks(args, action="create")


def remove_schedule() -> None:
    """Delete the TempCleaner scheduled task if present.

    Locale-safe: if delete fails, treat as success when ``schedule_exists()``
    is still false (task already absent; avoids English-only stderr matching).

    Raises:
        RuntimeError: If ``schtasks`` fails and the task still exists.
    """
    args = build_schtasks_delete_args(TASK_NAME)
    result = _subprocess_run(args)
    if result.returncode == 0:
        logger.info("Removed scheduled task %r", TASK_NAME)
        return
    # Locale-safe absence check: prefer query over English stderr phrases
    try:
        if not schedule_exists():
            logger.info("Scheduled task %r already absent", TASK_NAME)
            return
    except OSError as exc:
        logger.warning("schedule_exists after failed delete: %s", exc)
    stderr = (result.stderr or "").strip()
    stdout = (result.stdout or "").strip()
    msg = stderr or stdout or f"schtasks exit {result.returncode}"
    raise RuntimeError(f"Failed to remove scheduled task: {msg}")


def schedule_exists() -> bool:
    """Return True if the TempCleaner task is registered."""
    args = build_schtasks_query_args(TASK_NAME)
    result = _subprocess_run(args)
    return result.returncode == 0


def _subprocess_run(args: Sequence[str]) -> subprocess.CompletedProcess[str]:
    """Run argv with capture; on Windows hide the console via CREATE_NO_WINDOW."""
    if sys.platform == "win32":
        return subprocess.run(
            list(args),
            capture_output=True,
            text=True,
            check=False,
            creationflags=_CREATE_NO_WINDOW,
        )
    return subprocess.run(
        list(args),
        capture_output=True,
        text=True,
        check=False,
    )


def _run_schtasks(args: Sequence[str], *, action: str) -> subprocess.CompletedProcess[str]:
    logger.info("schtasks %s: %s", action, list(args))
    result = _subprocess_run(args)
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()
        stdout = (result.stdout or "").strip()
        msg = stderr or stdout or f"schtasks exit {result.returncode}"
        logger.error("schtasks %s failed: %s", action, msg)
        raise RuntimeError(f"Failed to {action} scheduled task: {msg}")
    logger.info("schtasks %s ok", action)
    return result
