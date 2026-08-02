"""Registry of clean targets and default enablement."""

from __future__ import annotations

import fnmatch
from pathlib import Path

from tempcleaner.core.models import CleanTargetSpec, RiskLevel
from tempcleaner.platform_win import paths as win_paths


def _single_path_roots(path_fn):
    """Build resolve_paths / allowed_roots callables for one specific directory.

    Never use drive roots or the user profile root as allowed_roots.
    """

    def resolve_paths() -> list[Path]:
        return [path_fn()]

    def allowed_roots() -> list[Path]:
        return [path_fn()]

    return resolve_paths, allowed_roots


def _thumbcache_name_predicate(path: Path) -> bool:
    name = path.name
    return bool(
        fnmatch.fnmatch(name, "thumbcache_*.db")
        or fnmatch.fnmatch(name, "iconcache_*.db")
    )


def _build_targets() -> dict[str, CleanTargetSpec]:
    user_temp_paths, user_temp_roots = _single_path_roots(win_paths.user_temp)
    windows_temp_paths, windows_temp_roots = _single_path_roots(win_paths.windows_temp)
    prefetch_paths, prefetch_roots = _single_path_roots(win_paths.prefetch)
    recent_paths, recent_roots = _single_path_roots(win_paths.recent_dir)
    thumb_paths, thumb_roots = _single_path_roots(win_paths.thumbcache_dir)
    do_paths, do_roots = _single_path_roots(win_paths.delivery_optimization)
    wud_paths, wud_roots = _single_path_roots(win_paths.windows_update_download)

    return {
        "user_temp": CleanTargetSpec(
            id="user_temp",
            name="User Temp",
            description="Files in the current user's TEMP directory.",
            risk=RiskLevel.SAFE,
            requires_admin=False,
            enabled_by_default=True,
            allow_scheduled_default=True,
            resolve_paths=user_temp_paths,
            allowed_roots=user_temp_roots,
        ),
        "windows_temp": CleanTargetSpec(
            id="windows_temp",
            name="Windows Temp",
            description="System temporary files under Windows\\Temp.",
            risk=RiskLevel.ELEVATED,
            requires_admin=True,
            enabled_by_default=True,
            allow_scheduled_default=True,
            resolve_paths=windows_temp_paths,
            allowed_roots=windows_temp_roots,
        ),
        "prefetch": CleanTargetSpec(
            id="prefetch",
            name="Prefetch",
            description="Windows Prefetch cache (may slow first launches after clean).",
            risk=RiskLevel.ELEVATED,
            requires_admin=True,
            enabled_by_default=False,
            allow_scheduled_default=False,
            resolve_paths=prefetch_paths,
            allowed_roots=prefetch_roots,
        ),
        "recent": CleanTargetSpec(
            id="recent",
            name="Recent Items",
            description="Recent documents and jump-list shortcuts.",
            risk=RiskLevel.SAFE,
            requires_admin=False,
            enabled_by_default=False,
            allow_scheduled_default=False,
            resolve_paths=recent_paths,
            allowed_roots=recent_roots,
        ),
        "thumbcache": CleanTargetSpec(
            id="thumbcache",
            name="Thumbnail Cache",
            description="Explorer thumbnail and icon cache databases.",
            risk=RiskLevel.SAFE,
            requires_admin=False,
            enabled_by_default=False,
            allow_scheduled_default=False,
            resolve_paths=thumb_paths,
            allowed_roots=thumb_roots,
            name_predicate=_thumbcache_name_predicate,
        ),
        "delivery_optimization": CleanTargetSpec(
            id="delivery_optimization",
            name="Delivery Optimization",
            description="Windows Delivery Optimization download cache.",
            risk=RiskLevel.ELEVATED,
            requires_admin=True,
            enabled_by_default=False,
            allow_scheduled_default=False,
            resolve_paths=do_paths,
            allowed_roots=do_roots,
        ),
        "windows_update_download": CleanTargetSpec(
            id="windows_update_download",
            name="Windows Update Downloads",
            description="SoftwareDistribution\\Download cache (advanced).",
            risk=RiskLevel.ADVANCED,
            requires_admin=True,
            enabled_by_default=False,
            allow_scheduled_default=False,
            resolve_paths=wud_paths,
            allowed_roots=wud_roots,
        ),
    }


_TARGETS: dict[str, CleanTargetSpec] | None = None


def all_targets() -> dict[str, CleanTargetSpec]:
    global _TARGETS
    if _TARGETS is None:
        _TARGETS = _build_targets()
    return _TARGETS


def get_target(target_id: str) -> CleanTargetSpec:
    targets = all_targets()
    try:
        return targets[target_id]
    except KeyError as exc:
        raise KeyError(f"Unknown clean target: {target_id}") from exc


def default_enabled_ids() -> list[str]:
    return [tid for tid, spec in all_targets().items() if spec.enabled_by_default]
