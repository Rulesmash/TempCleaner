"""Tests for byte formatting and logging setup utilities."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path

from tempcleaner.util.sizing import format_bytes


def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024).startswith("1")
    assert "KB" in format_bytes(1024) or "KiB" in format_bytes(1024)


def test_format_bytes_units_1024_based_kb_mb_gb():
    """Use 1024-based KB/MB/GB labels consistently."""
    assert format_bytes(0) == "0 B"
    assert format_bytes(512) == "512 B"
    assert format_bytes(1023) == "1023 B"
    assert format_bytes(1024) == "1.0 KB"
    assert format_bytes(1536) == "1.5 KB"
    assert format_bytes(1024 * 1024) == "1.0 MB"
    assert format_bytes(int(1.5 * 1024 * 1024)) == "1.5 MB"
    assert format_bytes(1024**3) == "1.0 GB"
    assert format_bytes(int(1.5 * 1024**3)) == "1.5 GB"
    assert format_bytes(1024**4) == "1.0 TB"


def test_format_bytes_rejects_or_handles_negative():
    # Negative sizes are not expected; format absolute or raise cleanly.
    # Implementation uses absolute value for display.
    result = format_bytes(-1024)
    assert result.startswith(("-", "1"))
    assert "KB" in result or "B" in result


def test_setup_logging_returns_dated_log_path(tmp_path: Path):
    from tempcleaner.util.logging_setup import setup_logging

    log_file = setup_logging(level="DEBUG", log_dir=tmp_path)
    today = datetime.now(tz=timezone.utc).astimezone().strftime("%Y%m%d")
    assert log_file == tmp_path / f"tempcleaner-{today}.log"
    assert log_file.parent == tmp_path
    assert log_file.name.startswith("tempcleaner-")
    assert log_file.suffix == ".log"


def test_setup_logging_creates_log_dir(tmp_path: Path):
    from tempcleaner.util.logging_setup import setup_logging

    nested = tmp_path / "a" / "b" / "logs"
    log_file = setup_logging(log_dir=nested)
    assert nested.is_dir()
    assert log_file.parent == nested


def test_setup_logging_writes_to_file(tmp_path: Path):
    from tempcleaner.util.logging_setup import setup_logging

    log_file = setup_logging(level="INFO", log_dir=tmp_path)
    logger = logging.getLogger("tempcleaner.test_sizing")
    logger.info("task6-log-probe-message")
    # Flush handlers so content is on disk
    for handler in logging.getLogger().handlers:
        handler.flush()
    for handler in logging.getLogger("tempcleaner").handlers:
        handler.flush()

    text = log_file.read_text(encoding="utf-8")
    assert "task6-log-probe-message" in text


def test_setup_logging_accepts_level_case_insensitive(tmp_path: Path):
    from tempcleaner.util.logging_setup import setup_logging

    log_file = setup_logging(level="debug", log_dir=tmp_path)
    assert log_file.exists() or log_file.parent.is_dir()
    # DEBUG should allow debug messages through
    logger = logging.getLogger("tempcleaner")
    assert logger.getEffectiveLevel() <= logging.DEBUG or logging.getLogger().level <= logging.DEBUG
