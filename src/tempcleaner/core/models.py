from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Callable


class RiskLevel(Enum):
    SAFE = "safe"
    ELEVATED = "elevated"
    ADVANCED = "advanced"


@dataclass
class CleanTargetSpec:
    id: str
    name: str
    description: str
    risk: RiskLevel
    requires_admin: bool
    enabled_by_default: bool
    allow_scheduled_default: bool
    resolve_paths: Callable[[], list[Path]]
    allowed_roots: Callable[[], list[Path]]


@dataclass
class TargetScanStats:
    target_id: str
    path: Path
    file_count: int
    dir_count: int
    total_bytes: int
    errors: list[str] = field(default_factory=list)


@dataclass
class TargetCleanStats(TargetScanStats):
    deleted_files: int = 0
    deleted_dirs: int = 0
    skipped: int = 0
    failed: int = 0
    bytes_freed: int = 0


@dataclass
class EngineReport:
    action: str
    targets: list[TargetScanStats | TargetCleanStats]
    cancelled: bool
