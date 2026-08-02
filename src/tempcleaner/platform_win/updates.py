"""Optional GitHub Releases update check (stdlib urllib only).

Never raises to the caller on network/parse failure: returns
``(False, None, None)`` and logs a warning instead.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger("tempcleaner.platform_win.updates")

DEFAULT_RELEASES_URL = (
    "https://api.github.com/repos/Rulesmash/TempCleaner/releases/latest"
)

# Leading digits from a version segment (e.g. "1", "0rc1" -> 0, "12b" -> 12)
_SEGMENT_RE = re.compile(r"^(\d+)")


def version_tuple(version: str) -> tuple[int, ...]:
    """Parse a version / tag string into a comparable int tuple.

    Accepts forms like ``2.0.1``, ``v2.0.1``, ``V1.9.9``. Non-digit tails on
    a segment are ignored (``2.0.1rc1`` → ``(2, 0, 1)``). Empty / unparsable
    input yields ``(0,)``.
    """
    s = (version or "").strip()
    if s[:1] in ("v", "V"):
        s = s[1:]
    if not s:
        return (0,)

    parts: list[int] = []
    for segment in s.split("."):
        m = _SEGMENT_RE.match(segment.strip())
        parts.append(int(m.group(1)) if m else 0)
    return tuple(parts) if parts else (0,)


def is_newer(candidate: str, current: str) -> bool:
    """Return True if *candidate* is strictly newer than *current*."""
    return version_tuple(candidate) > version_tuple(current)


def check_latest_release(
    current: str,
    url: str = DEFAULT_RELEASES_URL,
    timeout: float = 5.0,
) -> tuple[bool, str | None, str | None]:
    """Query GitHub Releases for the latest tag and compare to *current*.

    Returns:
        ``(update_available, latest_tag, html_url)``. On any network or
        parse error: ``(False, None, None)`` after logging a warning —
        never raises.
    """
    try:
        req = urllib.request.Request(
            url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "TempCleaner-UpdateCheck",
            },
            method="GET",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        data: Any = json.loads(raw.decode("utf-8"))
        if not isinstance(data, dict):
            logger.warning("Update check: unexpected JSON type %s", type(data).__name__)
            return (False, None, None)

        tag = data.get("tag_name") or data.get("name")
        if tag is None or str(tag).strip() == "":
            logger.warning("Update check: release payload missing tag_name")
            return (False, None, None)

        latest_tag = str(tag).strip()
        html_url_val = data.get("html_url")
        html_url = str(html_url_val).strip() if html_url_val else None
        if html_url == "":
            html_url = None

        available = is_newer(latest_tag, current)
        logger.info(
            "Update check: current=%s latest=%s available=%s",
            current,
            latest_tag,
            available,
        )
        return (available, latest_tag, html_url)
    except (
        urllib.error.URLError,
        TimeoutError,
        OSError,
        ValueError,
        TypeError,
        json.JSONDecodeError,
    ) as exc:
        logger.warning("Update check failed: %s", exc)
        return (False, None, None)
    except Exception as exc:  # noqa: BLE001 — must never crash GUI/CLI
        logger.warning("Update check failed (unexpected): %s", exc)
        return (False, None, None)
