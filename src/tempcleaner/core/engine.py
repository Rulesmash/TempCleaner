"""Scan / dry-run / clean orchestration for TempCleaner."""

from __future__ import annotations

import os
import shutil
import threading
from pathlib import Path

from tempcleaner.core.models import (
    CleanTargetSpec,
    EngineReport,
    TargetCleanStats,
    TargetScanStats,
)
from tempcleaner.core.safety import SafetyError, assert_path_safe, is_forbidden_top_level


class NotConfirmedError(PermissionError):
    """Raised when clean is requested without confirmed=True."""


class CleanEngine:
    """Orchestrates measuring and permanently deleting allowlisted target children."""

    def __init__(self, targets: dict[str, CleanTargetSpec] | None = None) -> None:
        if targets is None:
            from tempcleaner.core.targets import all_targets

            self._targets = all_targets()
        else:
            self._targets = targets

    def scan(
        self,
        target_ids: list[str],
        cancel_event: threading.Event | None = None,
    ) -> EngineReport:
        return self._run(target_ids, action="scan", do_delete=False, cancel_event=cancel_event)

    def dry_run(
        self,
        target_ids: list[str],
        cancel_event: threading.Event | None = None,
    ) -> EngineReport:
        return self._run(target_ids, action="dry_run", do_delete=False, cancel_event=cancel_event)

    def clean(
        self,
        target_ids: list[str],
        *,
        confirmed: bool,
        cancel_event: threading.Event | None = None,
    ) -> EngineReport:
        if not confirmed:
            raise NotConfirmedError("Clean requires confirmed=True")
        return self._run(target_ids, action="clean", do_delete=True, cancel_event=cancel_event)

    def _run(
        self,
        target_ids: list[str],
        *,
        action: str,
        do_delete: bool,
        cancel_event: threading.Event | None,
    ) -> EngineReport:
        results: list[TargetScanStats | TargetCleanStats] = []
        cancelled = False

        for target_id in target_ids:
            if cancel_event is not None and cancel_event.is_set():
                cancelled = True
                break

            if target_id not in self._targets:
                results.append(
                    TargetScanStats(
                        target_id=target_id,
                        path=Path("."),
                        file_count=0,
                        dir_count=0,
                        total_bytes=0,
                        errors=[f"Unknown target id: {target_id}"],
                    )
                )
                continue

            spec = self._targets[target_id]
            try:
                roots = list(spec.resolve_paths())
                allowed = list(spec.allowed_roots())
            except OSError as exc:
                results.append(
                    TargetScanStats(
                        target_id=target_id,
                        path=Path("."),
                        file_count=0,
                        dir_count=0,
                        total_bytes=0,
                        errors=[f"Failed to resolve paths: {exc}"],
                    )
                )
                continue

            for root in roots:
                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    break

                stats = self._process_root(
                    spec=spec,
                    root=root,
                    allowed_roots=allowed,
                    do_delete=do_delete,
                    cancel_event=cancel_event,
                )
                results.append(stats)

                if cancel_event is not None and cancel_event.is_set():
                    cancelled = True
                    break

            if cancelled:
                break

        return EngineReport(action=action, targets=results, cancelled=cancelled)

    def _process_root(
        self,
        *,
        spec: CleanTargetSpec,
        root: Path,
        allowed_roots: list[Path],
        do_delete: bool,
        cancel_event: threading.Event | None,
    ) -> TargetScanStats | TargetCleanStats:
        errors: list[str] = []
        file_count = 0
        dir_count = 0
        total_bytes = 0
        deleted_files = 0
        deleted_dirs = 0
        skipped = 0
        failed = 0
        bytes_freed = 0

        if not root.exists():
            msg = f"Path does not exist: {root}"
            errors.append(msg)
            if do_delete:
                return TargetCleanStats(
                    target_id=spec.id,
                    path=root,
                    file_count=0,
                    dir_count=0,
                    total_bytes=0,
                    errors=errors,
                )
            return TargetScanStats(
                target_id=spec.id,
                path=root,
                file_count=0,
                dir_count=0,
                total_bytes=0,
                errors=errors,
            )

        if is_forbidden_top_level(root):
            msg = f"Refusing forbidden top-level path: {root}"
            errors.append(msg)
            if do_delete:
                return TargetCleanStats(
                    target_id=spec.id,
                    path=root,
                    file_count=0,
                    dir_count=0,
                    total_bytes=0,
                    errors=errors,
                )
            return TargetScanStats(
                target_id=spec.id,
                path=root,
                file_count=0,
                dir_count=0,
                total_bytes=0,
                errors=errors,
            )

        try:
            children = list(root.iterdir())
        except OSError as exc:
            errors.append(f"Cannot list {root}: {exc}")
            if do_delete:
                return TargetCleanStats(
                    target_id=spec.id,
                    path=root,
                    file_count=0,
                    dir_count=0,
                    total_bytes=0,
                    errors=errors,
                )
            return TargetScanStats(
                target_id=spec.id,
                path=root,
                file_count=0,
                dir_count=0,
                total_bytes=0,
                errors=errors,
            )

        if spec.name_predicate is not None:
            children = [c for c in children if spec.name_predicate(c)]

        for child in children:
            if cancel_event is not None and cancel_event.is_set():
                errors.append("Cancelled")
                break

            try:
                safe_child = assert_path_safe(child, allowed_roots)
            except SafetyError as exc:
                errors.append(str(exc))
                failed += 1
                continue

            try:
                is_dir = safe_child.is_dir()
                is_file = safe_child.is_file()
            except OSError as exc:
                errors.append(f"Cannot stat {safe_child}: {exc}")
                skipped += 1
                continue

            if is_file:
                try:
                    size = safe_child.stat().st_size
                except OSError as exc:
                    errors.append(f"Cannot stat {safe_child}: {exc}")
                    skipped += 1
                    continue
                file_count += 1
                total_bytes += size
                if do_delete:
                    try:
                        safe_child.unlink()
                        deleted_files += 1
                        bytes_freed += size
                    except OSError as exc:
                        errors.append(f"Failed to delete {safe_child}: {exc}")
                        skipped += 1
            elif is_dir:
                fc, dc, tb, walk_errors = _measure_directory(safe_child)
                errors.extend(walk_errors)
                # Count the directory itself plus nested dirs/files
                file_count += fc
                dir_count += 1 + dc
                total_bytes += tb
                if do_delete:
                    try:
                        shutil.rmtree(safe_child)
                        deleted_dirs += 1
                        bytes_freed += tb
                    except OSError as exc:
                        errors.append(f"Failed to delete {safe_child}: {exc}")
                        skipped += 1
            else:
                # Symlinks / special nodes: treat as files if unlinkable
                try:
                    size = safe_child.stat().st_size
                except OSError:
                    size = 0
                file_count += 1
                total_bytes += size
                if do_delete:
                    try:
                        if safe_child.is_symlink() or safe_child.is_file():
                            safe_child.unlink()
                        else:
                            shutil.rmtree(safe_child)
                        deleted_files += 1
                        bytes_freed += size
                    except OSError as exc:
                        errors.append(f"Failed to delete {safe_child}: {exc}")
                        skipped += 1

        if do_delete:
            return TargetCleanStats(
                target_id=spec.id,
                path=root,
                file_count=file_count,
                dir_count=dir_count,
                total_bytes=total_bytes,
                errors=errors,
                deleted_files=deleted_files,
                deleted_dirs=deleted_dirs,
                skipped=skipped,
                failed=failed,
                bytes_freed=bytes_freed,
            )
        return TargetScanStats(
            target_id=spec.id,
            path=root,
            file_count=file_count,
            dir_count=dir_count,
            total_bytes=total_bytes,
            errors=errors,
        )


def _measure_directory(path: Path) -> tuple[int, int, int, list[str]]:
    """Walk *path* and return (file_count, nested_dir_count, total_bytes, errors).

    nested_dir_count excludes *path* itself (caller may add 1 for the root child).
    """
    file_count = 0
    dir_count = 0
    total_bytes = 0
    errors: list[str] = []

    try:
        for dirpath, dirnames, filenames in os.walk(path, topdown=True, onerror=None):
            # Nested directories only (os.walk yields path itself first)
            if Path(dirpath) != path:
                dir_count += 1
            for name in filenames:
                fp = Path(dirpath) / name
                try:
                    total_bytes += fp.stat().st_size
                    file_count += 1
                except OSError as exc:
                    errors.append(f"Cannot stat {fp}: {exc}")
            # Also count dirs that os.walk may not descend into later if removed;
            # dirnames are relative children of dirpath — counted when visited.
            _ = dirnames  # keep structure explicit
    except OSError as exc:
        errors.append(f"Cannot walk {path}: {exc}")

    return file_count, dir_count, total_bytes, errors
