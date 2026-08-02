"""Tests for GitHub Releases version compare and check_latest_release."""

from __future__ import annotations

import json
import urllib.error
from typing import Any

import pytest

from tempcleaner.platform_win.updates import (
    check_latest_release,
    is_newer,
    version_tuple,
)


def test_is_newer() -> None:
    assert is_newer("2.0.1", "2.0.0") is True
    assert is_newer("2.0.0", "2.0.0") is False
    assert is_newer("1.9.9", "2.0.0") is False


def test_version_tuple_strips_v_prefix() -> None:
    assert version_tuple("v2.0.1") == (2, 0, 1)
    assert version_tuple("V2.0.0") == (2, 0, 0)
    assert version_tuple("2.0.0") == (2, 0, 0)


def test_is_newer_with_v_prefix() -> None:
    assert is_newer("v2.0.1", "2.0.0") is True
    assert is_newer("2.0.1", "v2.0.0") is True
    assert is_newer("v2.0.0", "v2.0.0") is False


def test_version_tuple_empty() -> None:
    assert version_tuple("") == (0,)
    assert version_tuple("   ") == (0,)


def test_check_latest_release_network_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise urllib.error.URLError("offline")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert check_latest_release("2.0.0") == (False, None, None)


def test_check_latest_release_timeout(monkeypatch: pytest.MonkeyPatch) -> None:
    def boom(*_a: Any, **_k: Any) -> Any:
        raise TimeoutError("timed out")

    monkeypatch.setattr("urllib.request.urlopen", boom)
    assert check_latest_release("2.0.0") == (False, None, None)


class _FakeResponse:
    def __init__(self, payload: dict[str, Any]) -> None:
        self._body = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self) -> _FakeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None


def test_check_latest_release_update_available(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_open(*_a: Any, **_k: Any) -> _FakeResponse:
        return _FakeResponse(
            {
                "tag_name": "v2.0.1",
                "html_url": "https://github.com/Rulesmash/TempCleaner/releases/tag/v2.0.1",
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    available, tag, url = check_latest_release("2.0.0")
    assert available is True
    assert tag == "v2.0.1"
    assert url is not None
    assert "releases" in url


def test_check_latest_release_already_current(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_open(*_a: Any, **_k: Any) -> _FakeResponse:
        return _FakeResponse(
            {
                "tag_name": "v2.0.0",
                "html_url": "https://github.com/Rulesmash/TempCleaner/releases/tag/v2.0.0",
            }
        )

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    available, tag, url = check_latest_release("2.0.0")
    assert available is False
    assert tag == "v2.0.0"
    assert url is not None


def test_check_latest_release_bad_json(monkeypatch: pytest.MonkeyPatch) -> None:
    class BadResp:
        def read(self) -> bytes:
            return b"not-json{"

        def __enter__(self) -> BadResp:
            return self

        def __exit__(self, *_a: object) -> None:
            return None

    monkeypatch.setattr("urllib.request.urlopen", lambda *_a, **_k: BadResp())
    assert check_latest_release("2.0.0") == (False, None, None)
