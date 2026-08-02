"""File logging under AppData (log dir injectable for tests)."""

from __future__ import annotations

import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from tempcleaner.platform_win.paths import appdata_dir


def setup_logging(level: str = "INFO", log_dir: Path | None = None) -> Path:
    """Configure the root and ``tempcleaner`` loggers for file + stderr.

    Log file: ``tempcleaner-YYYYMMDD.log`` under *log_dir* (default
    ``%AppData%\\TempCleaner\\logs``). Creates parent directories as needed.

    Returns the path to the log file.
    """
    if log_dir is None:
        log_dir = appdata_dir() / "logs"
    log_dir = Path(log_dir)
    log_dir.mkdir(parents=True, exist_ok=True)

    date_str = datetime.now(tz=timezone.utc).astimezone().strftime("%Y%m%d")
    log_file = log_dir / f"tempcleaner-{date_str}.log"

    log_level = getattr(logging, str(level).upper(), None)
    if not isinstance(log_level, int):
        log_level = logging.INFO

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(log_level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stderr)
    stream_handler.setLevel(log_level)
    stream_handler.setFormatter(formatter)

    # Replace root handlers so repeated setup is idempotent (force=True: 3.8+).
    logging.basicConfig(
        level=log_level,
        handlers=[file_handler, stream_handler],
        force=True,
    )

    package_logger = logging.getLogger("tempcleaner")
    package_logger.setLevel(log_level)

    return log_file
