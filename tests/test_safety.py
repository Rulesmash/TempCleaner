from pathlib import Path

import pytest

from tempcleaner.core.safety import SafetyError, assert_path_safe, is_forbidden_top_level


def test_accepts_path_under_allowed_root(tmp_path: Path):
    child = tmp_path / "a" / "b.txt"
    child.parent.mkdir(parents=True)
    child.write_text("x", encoding="utf-8")
    assert assert_path_safe(child, [tmp_path]) == child.resolve()


def test_rejects_path_outside_allowed_root(tmp_path: Path):
    outside = tmp_path.parent / "outside-not-allowed"
    with pytest.raises(SafetyError):
        assert_path_safe(outside, [tmp_path])


def test_rejects_drive_root_even_if_listed():
    root = Path("C:\\")
    with pytest.raises(SafetyError):
        assert_path_safe(root, [root])


def test_is_forbidden_top_level_rejects_drive_root():
    assert is_forbidden_top_level(Path("C:\\")) is True


def test_is_forbidden_top_level_rejects_home():
    assert is_forbidden_top_level(Path.home()) is True


def test_is_forbidden_top_level_accepts_subdir_of_home(tmp_path: Path):
    # tmp_path is typically under home or system temp; either way not equal to home root
    assert is_forbidden_top_level(tmp_path) is False
    nested = Path.home() / "AppData"
    if nested.exists():
        assert is_forbidden_top_level(nested) is False
