from pathlib import Path

from tempcleaner.core.targets import all_targets, default_enabled_ids, get_target


def test_all_expected_target_ids_present():
    ids = set(all_targets())
    assert ids == {
        "user_temp",
        "windows_temp",
        "prefetch",
        "recent",
        "thumbcache",
        "delivery_optimization",
        "windows_update_download",
    }


def test_prefetch_defaults_off_and_requires_admin():
    t = get_target("prefetch")
    assert t.enabled_by_default is False
    assert t.requires_admin is True


def test_default_enabled_includes_user_and_windows_temp():
    enabled = set(default_enabled_ids())
    assert "user_temp" in enabled
    assert "windows_temp" in enabled
    assert "prefetch" not in enabled
    assert "windows_update_download" not in enabled


def test_recent_name_predicate_lnk_only():
    t = get_target("recent")
    assert t.name_predicate is not None
    assert t.name_predicate(Path("document.docx.lnk")) is True
    assert t.name_predicate(Path("foo.LNK")) is True  # case-insensitive via fnmatch
    assert t.name_predicate(Path("AutomaticDestinations-ms")) is False
    assert t.name_predicate(Path("readme.txt")) is False
    assert t.name_predicate(Path("folder")) is False
