"""Human-readable byte size formatting (1024-based KB/MB/GB)."""

from __future__ import annotations

_UNITS = ("B", "KB", "MB", "GB", "TB", "PB")


def format_bytes(n: int) -> str:
    """Format *n* bytes as a human-readable string using 1024-based units.

    Examples:
        0 -> "0 B"
        1024 -> "1.0 KB"
        1536 -> "1.5 KB"
        1.5 * 1024**3 -> "1.5 GB"
    """
    sign = "-" if n < 0 else ""
    value = float(abs(n))
    unit_index = 0
    while value >= 1024.0 and unit_index < len(_UNITS) - 1:
        value /= 1024.0
        unit_index += 1
    if unit_index == 0:
        return f"{sign}{int(value)} B"
    return f"{sign}{value:.1f} {_UNITS[unit_index]}"
