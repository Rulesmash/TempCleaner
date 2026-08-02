from pathlib import Path
import threading

import pytest

from tempcleaner.core.engine import CleanEngine, NotConfirmedError
from tempcleaner.core.models import CleanTargetSpec, RiskLevel


def _spec(tmp_path: Path, tid: str = "t1") -> CleanTargetSpec:
    root = tmp_path / tid
    root.mkdir()
    return CleanTargetSpec(
        id=tid,
        name="Test",
        description="test",
        risk=RiskLevel.SAFE,
        requires_admin=False,
        enabled_by_default=True,
        allow_scheduled_default=True,
        resolve_paths=lambda r=root: [r],
        allowed_roots=lambda r=root: [r],
    )


def test_scan_counts_files_and_bytes(tmp_path: Path):
    spec = _spec(tmp_path)
    root = spec.resolve_paths()[0]
    f = root / "a.txt"
    f.write_bytes(b"hello")
    eng = CleanEngine({spec.id: spec})
    report = eng.scan([spec.id])
    assert report.targets[0].file_count == 1
    assert report.targets[0].total_bytes == 5


def test_clean_requires_confirmed(tmp_path: Path):
    spec = _spec(tmp_path)
    eng = CleanEngine({spec.id: spec})
    with pytest.raises(NotConfirmedError):
        eng.clean([spec.id], confirmed=False)


def test_clean_deletes_files(tmp_path: Path):
    spec = _spec(tmp_path)
    root = spec.resolve_paths()[0]
    f = root / "a.txt"
    f.write_text("x", encoding="utf-8")
    eng = CleanEngine({spec.id: spec})
    report = eng.clean([spec.id], confirmed=True)
    assert not f.exists()
    assert report.targets[0].deleted_files == 1


def test_dry_run_does_not_delete(tmp_path: Path):
    spec = _spec(tmp_path)
    root = spec.resolve_paths()[0]
    f = root / "a.txt"
    f.write_text("x", encoding="utf-8")
    eng = CleanEngine({spec.id: spec})
    eng.dry_run([spec.id])
    assert f.exists()


def test_clean_preserves_root_folder(tmp_path: Path):
    spec = _spec(tmp_path)
    root = spec.resolve_paths()[0]
    (root / "a.txt").write_text("x", encoding="utf-8")
    eng = CleanEngine({spec.id: spec})
    eng.clean([spec.id], confirmed=True)
    assert root.exists()
    assert root.is_dir()


def test_name_predicate_filters_children(tmp_path: Path):
    root = tmp_path / "thumb"
    root.mkdir()
    keep = root / "keep.txt"
    drop = root / "thumbcache_1.db"
    keep.write_text("keep", encoding="utf-8")
    drop.write_bytes(b"dbdata")
    spec = CleanTargetSpec(
        id="thumb",
        name="Thumb",
        description="test",
        risk=RiskLevel.SAFE,
        requires_admin=False,
        enabled_by_default=False,
        allow_scheduled_default=False,
        resolve_paths=lambda r=root: [r],
        allowed_roots=lambda r=root: [r],
        name_predicate=lambda p: p.name.startswith("thumbcache_"),
    )
    eng = CleanEngine({spec.id: spec})
    report = eng.scan([spec.id])
    assert report.targets[0].file_count == 1
    assert report.targets[0].total_bytes == 6
    eng.clean([spec.id], confirmed=True)
    assert keep.exists()
    assert not drop.exists()


def test_scan_missing_root_notes_error(tmp_path: Path):
    missing = tmp_path / "does-not-exist"
    spec = CleanTargetSpec(
        id="missing",
        name="Missing",
        description="test",
        risk=RiskLevel.SAFE,
        requires_admin=False,
        enabled_by_default=True,
        allow_scheduled_default=True,
        resolve_paths=lambda m=missing: [m],
        allowed_roots=lambda m=missing: [m],
    )
    eng = CleanEngine({spec.id: spec})
    report = eng.scan([spec.id])
    stats = report.targets[0]
    assert stats.file_count == 0
    assert stats.total_bytes == 0
    assert stats.errors


def test_cancel_between_targets(tmp_path: Path):
    s1 = _spec(tmp_path, "t1")
    s2 = _spec(tmp_path, "t2")
    (s1.resolve_paths()[0] / "a.txt").write_text("a", encoding="utf-8")
    (s2.resolve_paths()[0] / "b.txt").write_text("b", encoding="utf-8")
    cancel = threading.Event()
    cancel.set()
    eng = CleanEngine({s1.id: s1, s2.id: s2})
    report = eng.scan([s1.id, s2.id], cancel_event=cancel)
    assert report.cancelled is True
