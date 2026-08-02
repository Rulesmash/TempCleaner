# TempCleaner v2.0 Revamp Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace TempCleaner 1.x with a modular Windows product (v2.0.0): ttk multi-tab GUI, expanded targets, dry-run/confirm guardrails, settings, Task Scheduler integration, CLI, tests, CI, and full documentation—then push `main` and delete remote `TestA`.

**Architecture:** Package under `src/tempcleaner/` with layered `core` (engine/targets/safety), `config`, `platform_win`, `ui`, and `util`. Core never imports Tkinter. Runtime is stdlib-only; dev deps are pytest/ruff/pyinstaller. Settings and logs live under `%AppData%\TempCleaner\`.

**Tech Stack:** Python 3.10+, Tkinter/ttk, `ctypes` (admin), `urllib` (update check), `subprocess` (`schtasks`), pytest, ruff, PyInstaller (dev), GitHub Actions `windows-latest`.

**Spec:** `docs/superpowers/specs/2026-08-03-tempcleaner-v2-revamp-design.md`

## Global Constraints

- Platform: **Windows only**; refuse start on non-Windows with a clear message.
- Python: **3.10+**.
- Runtime dependencies: **stdlib only** (no ttkbootstrap, send2trash, pystray, etc.).
- Delete model: **permanent delete** after confirm (GUI) or `--yes` (CLI); dry-run supported.
- Path safety: only allowlisted roots per target; never delete drive roots or user profile root.
- Errors: catch `OSError` / `PermissionError` (and subclasses); **no bare `except:`**.
- Version: ship as **2.0.0**.
- License: keep **GNU GPLv3**.
- Git: preserve history on `main` (no force-push unless user explicitly asks); delete remote **`TestA`** after v2 lands.
- Project root: `d:\Docs\My Apps\TempCleaner\Release\TempCleaner`.
- Tests must use `tmp_path` only—never delete real `C:\Windows\*` in tests.
- UI: modern **ttk**, not PNG button layout.
- Prefetch default **off**; advanced targets gated by settings; require-dry-run default **on**.

---

## File map (create unless noted)

| Path | Responsibility |
|------|----------------|
| `pyproject.toml` | Package metadata, entry point, optional `[dev]` |
| `.gitignore` | Python/venv/build/IDE/OS/logs |
| `src/tempcleaner/__init__.py` | Package exports / version re-export |
| `src/tempcleaner/__main__.py` | `python -m tempcleaner` |
| `src/tempcleaner/version.py` | `__version__ = "2.0.0"` |
| `src/tempcleaner/app.py` | Bootstrap GUI or CLI dispatch |
| `src/tempcleaner/core/models.py` | Dataclasses for targets and results |
| `src/tempcleaner/core/safety.py` | Path allowlist validation |
| `src/tempcleaner/core/targets.py` | Built-in target registry |
| `src/tempcleaner/core/engine.py` | Scan / dry-run / clean orchestration |
| `src/tempcleaner/config/defaults.py` | Default settings dict |
| `src/tempcleaner/config/settings.py` | Load/save JSON settings |
| `src/tempcleaner/platform_win/admin.py` | Elevation detect + relaunch |
| `src/tempcleaner/platform_win/paths.py` | AppData, known Windows paths |
| `src/tempcleaner/platform_win/scheduler.py` | schtasks wrapper |
| `src/tempcleaner/platform_win/updates.py` | GitHub Releases check |
| `src/tempcleaner/util/logging_setup.py` | File logging under AppData |
| `src/tempcleaner/util/sizing.py` | Human-readable sizes |
| `src/tempcleaner/ui/*.py` | Main window, tabs, dialogs |
| `tests/test_*.py` | Unit tests |
| `.github/workflows/ci.yml` | Windows CI |
| `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/*` | Documentation |
| `scripts/build_exe.ps1`, `scripts/install_dev.ps1` | Dev/build helpers |
| Remove after cutover: root `main.py`, `Deleter.py`, `local_temp.py`, `percent_temp.py`, `prefetch.py`, obsolete PNG chrome |

---

### Task 1: Repository scaffold, package metadata, git wiring

**Files:**
- Create: `pyproject.toml`, `.gitignore`, `src/tempcleaner/__init__.py`, `src/tempcleaner/version.py`, `src/tempcleaner/__main__.py`, `tests/test_version.py`
- Keep: `LICENSE`, `docs/superpowers/specs/2026-08-03-tempcleaner-v2-revamp-design.md`, `docs/superpowers/plans/2026-08-03-tempcleaner-v2-revamp.md`, `assets/` icons as needed
- Modify later tasks remove legacy modules

**Interfaces:**
- Produces: `tempcleaner.version.__version__ == "2.0.0"`; installable editable package `tempcleaner`

- [ ] **Step 1: Initialize git from remote history (preserve commits)**

```powershell
cd "d:\Docs\My Apps\TempCleaner\Release\TempCleaner"
# If .git missing: clone into temp and move .git, OR
git clone https://github.com/Rulesmash/TempCleaner.git _upstream
Move-Item _upstream\.git .\.git
Remove-Item -Recurse -Force _upstream
git status
git checkout main
```

If clone fails (auth/network), `git init`, add remote, fetch, and checkout `main` with `git pull origin main --allow-unrelated-histories` only if needed—prefer clean clone overlay.

- [ ] **Step 2: Write `.gitignore`**

```gitignore
__pycache__/
*.py[cod]
*$py.class
.Python
.venv/
venv/
env/
dist/
build/
*.egg-info/
.eggs/
*.spec
.pytest_cache/
.mypy_cache/
.ruff_cache/
.coverage
htmlcov/
.idea/
.vscode/
*.code-workspace
Thumbs.db
Desktop.ini
.DS_Store
*.log
settings.local.json
*.exe
!assets/**
```

Do not ignore `docs/` or source under `src/`.

- [ ] **Step 3: Write `pyproject.toml`**

```toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "tempcleaner"
version = "2.0.0"
description = "Windows temp and cache cleaner with dry-run, confirmations, and scheduling"
readme = "README.md"
license = { text = "GPL-3.0-only" }
requires-python = ">=3.10"
authors = [{ name = "Rulesmash" }]
keywords = ["windows", "temp", "cleaner", "prefetch"]
classifiers = [
  "Environment :: Win32 (MS Windows)",
  "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
  "Operating System :: Microsoft :: Windows",
  "Programming Language :: Python :: 3",
  "Programming Language :: Python :: 3.10",
  "Programming Language :: Python :: 3.11",
  "Programming Language :: Python :: 3.12",
]
dependencies = []

[project.optional-dependencies]
dev = ["pytest>=8.0", "ruff>=0.6", "pyinstaller>=6.0"]

[project.scripts]
tempcleaner = "tempcleaner.app:main"

[project.urls]
Homepage = "https://github.com/Rulesmash/TempCleaner"
Issues = "https://github.com/Rulesmash/TempCleaner/issues"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

[tool.ruff]
line-length = 100
target-version = "py310"
```

- [ ] **Step 4: Write version module and package init**

`src/tempcleaner/version.py`:
```python
__version__ = "2.0.0"
```

`src/tempcleaner/__init__.py`:
```python
from tempcleaner.version import __version__

__all__ = ["__version__"]
```

`src/tempcleaner/__main__.py`:
```python
from tempcleaner.app import main

if __name__ == "__main__":
    raise SystemExit(main())
```

Temporary `src/tempcleaner/app.py` (until Task 8 expands it):
```python
def main(argv: list[str] | None = None) -> int:
    from tempcleaner.version import __version__
    print(f"TempCleaner {__version__}")
    return 0
```

- [ ] **Step 5: Write failing version test, then install and pass**

`tests/test_version.py`:
```python
from tempcleaner.version import __version__


def test_version_is_2_0_0():
    assert __version__ == "2.0.0"
```

```powershell
cd "d:\Docs\My Apps\TempCleaner\Release\TempCleaner"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
pytest tests/test_version.py -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add .gitignore pyproject.toml src/tempcleaner tests/test_version.py docs/superpowers
git status
git commit -m "chore: scaffold TempCleaner v2 package layout and tooling"
```

---

### Task 2: Core models and path safety

**Files:**
- Create: `src/tempcleaner/core/__init__.py`, `src/tempcleaner/core/models.py`, `src/tempcleaner/core/safety.py`, `tests/test_safety.py`

**Interfaces:**
- Produces:
  - `RiskLevel` enum: `SAFE`, `ELEVATED`, `ADVANCED`
  - `@dataclass CleanTargetSpec` fields: `id: str`, `name: str`, `description: str`, `risk: RiskLevel`, `requires_admin: bool`, `enabled_by_default: bool`, `allow_scheduled_default: bool`, `resolve_paths: Callable[[], list[Path]]`, `allowed_roots: Callable[[], list[Path]]`
  - `@dataclass TargetScanStats`: `target_id`, `path`, `file_count`, `dir_count`, `total_bytes`, `errors: list[str]`
  - `@dataclass TargetCleanStats`: extends scan fields with `deleted_files`, `deleted_dirs`, `skipped`, `failed`, `bytes_freed`
  - `@dataclass EngineReport`: `action: str`, `targets: list[TargetScanStats | TargetCleanStats]`, `cancelled: bool`
  - `assert_path_safe(path: Path, allowed_roots: list[Path]) -> Path` — resolves absolute path; raises `SafetyError` if invalid
  - `SafetyError(Exception)`

- [ ] **Step 1: Write failing safety tests**

```python
# tests/test_safety.py
from pathlib import Path
import pytest
from tempcleaner.core.safety import SafetyError, assert_path_safe


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
```

- [ ] **Step 2: Run tests — expect FAIL (import error)**

```powershell
pytest tests/test_safety.py -v
```

- [ ] **Step 3: Implement models and safety**

`models.py` — define enums/dataclasses as in Interfaces (use `from __future__ import annotations` and `enum.Enum`).

`safety.py`:
```python
from pathlib import Path


class SafetyError(ValueError):
    pass


def assert_path_safe(path: Path, allowed_roots: list[Path]) -> Path:
    resolved = path.expanduser().resolve(strict=False)
    if len(resolved.parts) <= 1:
        raise SafetyError(f"Refusing drive/root path: {resolved}")
    # Windows: Path('C:\\').parts may be ('C:\\',) — reject
    if resolved.parent == resolved:
        raise SafetyError(f"Refusing root path: {resolved}")
    roots = [r.expanduser().resolve(strict=False) for r in allowed_roots]
    for root in roots:
        try:
            resolved.relative_to(root)
            return resolved
        except ValueError:
            continue
    raise SafetyError(f"Path not under allowlisted roots: {resolved}")
```

Also reject user profile root if path equals `Path.home()` exactly when used as delete target (in engine, not only here). Add:

```python
def is_forbidden_top_level(path: Path) -> bool:
    resolved = path.resolve(strict=False)
    if resolved.parent == resolved:
        return True
    if resolved == Path.home().resolve(strict=False):
        return True
    return False
```

Update tests to cover home rejection via `is_forbidden_top_level`.

- [ ] **Step 4: Run tests — expect PASS**

```powershell
pytest tests/test_safety.py -v
```

- [ ] **Step 5: Commit**

```powershell
git add src/tempcleaner/core tests/test_safety.py
git commit -m "feat(core): add models and path safety guards"
```

---

### Task 3: Target registry

**Files:**
- Create: `src/tempcleaner/core/targets.py`, `src/tempcleaner/platform_win/paths.py`, `tests/test_targets.py`
- Create: `src/tempcleaner/platform_win/__init__.py`

**Interfaces:**
- Produces:
  - `get_known_paths() -> dict` helpers in `paths.py`: `user_temp()`, `windows_temp()`, `prefetch()`, `recent_dir()`, `thumbcache_dir()`, `delivery_optimization()`, `windows_update_download()`, `appdata_dir() -> Path` (`Path(os.environ['APPDATA']) / 'TempCleaner'`)
  - `all_targets() -> dict[str, CleanTargetSpec]`
  - `get_target(target_id: str) -> CleanTargetSpec`
  - `default_enabled_ids() -> list[str]`

Each target’s `resolve_paths` returns existing or intended dirs (list may include non-existent — engine skips missing). `allowed_roots` returns the same resolved parents used for safety.

Target IDs (exact): `user_temp`, `windows_temp`, `prefetch`, `recent`, `thumbcache`, `delivery_optimization`, `windows_update_download`.

- [ ] **Step 1: Write target registry tests**

```python
# tests/test_targets.py
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
```

- [ ] **Step 2: Run — expect FAIL**

- [ ] **Step 3: Implement `paths.py` and `targets.py`**

Use `os.environ.get("TEMP")`, `os.environ.get("LOCALAPPDATA")`, `Path(r"C:\Windows\Temp")`, `Path(r"C:\Windows\Prefetch")`, recent via `Path.home() / "AppData" / "Roaming" / "Microsoft" / "Windows" / "Recent"`, thumbcache via `Path(localappdata) / "Microsoft" / "Windows" / "Explorer"` (files matching `thumbcache_*.db` handled in engine as optional file filter — for v2 delete contents of that explorer cache folder carefully: only files named `thumbcache_*.db` and `iconcache_*.db`).

For thumbcache, prefer a target that only deletes matching filenames inside the Explorer folder (engine supports optional `name_predicate: Callable[[Path], bool] | None` on `CleanTargetSpec` — add field defaulting to `None` meaning all children).

Update `CleanTargetSpec` in models with:
```python
name_predicate: Callable[[Path], bool] | None = None
```

- [ ] **Step 4: pytest tests/test_targets.py -v — PASS**

- [ ] **Step 5: Commit**

```powershell
git commit -am "feat(core): register expanded clean targets"
```

---

### Task 4: Clean engine (scan / dry-run / clean) with TDD

**Files:**
- Create: `src/tempcleaner/core/engine.py`, `tests/test_engine.py`

**Interfaces:**
- Produces class `CleanEngine`:
  - `__init__(self, targets: dict[str, CleanTargetSpec] | None = None)`
  - `scan(self, target_ids: list[str], cancel_event: threading.Event | None = None) -> EngineReport`
  - `dry_run(self, target_ids: list[str], cancel_event: threading.Event | None = None) -> EngineReport` (alias of scan with `action="dry_run"`)
  - `clean(self, target_ids: list[str], *, confirmed: bool, cancel_event: threading.Event | None = None) -> EngineReport`
  - Raises `PermissionError` or custom `NotConfirmedError` if `confirmed` is False on clean
  - Skips missing roots; for each child, `assert_path_safe`; files `unlink`, dirs `shutil.rmtree`; count skips on `OSError`

- [ ] **Step 1: Write engine tests using tmp_path fake targets**

```python
# tests/test_engine.py
from pathlib import Path
import threading
from tempcleaner.core.models import CleanTargetSpec, RiskLevel
from tempcleaner.core.engine import CleanEngine, NotConfirmedError
import pytest


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
```

- [ ] **Step 2: Run — FAIL**

- [ ] **Step 3: Implement `engine.py`**

Core loop:
1. For each target id, resolve paths.
2. If path missing → stats with 0 and note in errors.
3. If `is_forbidden_top_level(path)` → error, skip.
4. List children; if `name_predicate`, filter.
5. For scan: accumulate size via `path.stat().st_size` for files; walk dirs for totals (use `os.walk` or `rglob` carefully).
6. For clean: delete children only (not the root folder itself), validate each child with `assert_path_safe(child, allowed_roots)`.
7. Honor `cancel_event.is_set()` between items; set `report.cancelled = True`.

- [ ] **Step 4: pytest tests/test_engine.py -v — PASS**

- [ ] **Step 5: Commit**

```powershell
git commit -am "feat(core): implement scan, dry-run, and clean engine"
```

---

### Task 5: Settings and defaults

**Files:**
- Create: `src/tempcleaner/config/__init__.py`, `src/tempcleaner/config/defaults.py`, `src/tempcleaner/config/settings.py`, `tests/test_settings.py`

**Interfaces:**
- Produces:
  - `DEFAULT_SETTINGS: dict` keys:
    - `selected_targets: list[str]`
    - `require_dry_run_before_clean: bool` → `True`
    - `allow_advanced_targets: bool` → `False`
    - `allow_prefetch_scheduled: bool` → `False`
    - `scheduled_clean_enabled: bool` → `False`
    - `scheduled_targets: list[str]`
    - `schedule_frequency: str` → `"daily"` (`daily`|`weekly`)
    - `schedule_time: str` → `"03:00"` (HH:MM)
    - `schedule_weekday: str` → `"MON"`
    - `close_minimizes: bool` → `False`
    - `check_updates_on_startup: bool` → `False`
    - `log_level: str` → `"INFO"`
  - `SettingsStore(path: Path | None = None)`
    - `load() -> dict`
    - `save(data: dict) -> None`
    - `update(**kwargs) -> dict`
  - Default path: `appdata_dir() / "settings.json"` (injectable for tests)

- [ ] **Step 1: Write tests with tmp_path settings file**

```python
def test_load_returns_defaults_when_missing(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    data = store.load()
    assert data["require_dry_run_before_clean"] is True
    assert data["check_updates_on_startup"] is False


def test_save_and_reload(tmp_path):
    store = SettingsStore(tmp_path / "settings.json")
    store.save({**store.load(), "close_minimizes": True})
    assert store.load()["close_minimizes"] is True
```

- [ ] **Step 2–4: Implement, pass tests, commit**

```powershell
git commit -am "feat(config): add JSON settings store with safe defaults"
```

---

### Task 6: Logging and sizing utilities

**Files:**
- Create: `src/tempcleaner/util/__init__.py`, `src/tempcleaner/util/sizing.py`, `src/tempcleaner/util/logging_setup.py`, `tests/test_sizing.py`

**Interfaces:**
- `format_bytes(n: int) -> str` (e.g. `1.5 GB`)
- `setup_logging(level: str = "INFO", log_dir: Path | None = None) -> Path` — configures root/`tempcleaner` logger to file `tempcleaner-YYYYMMDD.log` and stderr; returns log file path

- [ ] **Step 1: Test format_bytes**

```python
from tempcleaner.util.sizing import format_bytes

def test_format_bytes():
    assert format_bytes(0) == "0 B"
    assert format_bytes(1024).startswith("1")
    assert "KB" in format_bytes(1024) or "KiB" in format_bytes(1024)
```

Pick one unit style (**KB/MB/GB**, 1024-based) and use consistently in UI.

- [ ] **Step 2–4: Implement, pass, commit**

```powershell
git commit -am "feat(util): add byte formatting and AppData file logging"
```

---

### Task 7: Windows admin helpers

**Files:**
- Create: `src/tempcleaner/platform_win/admin.py`, `tests/test_admin.py`

**Interfaces:**
- `is_admin() -> bool` via `ctypes.windll.shell32.IsUserAnAdmin()`
- `relaunch_as_admin(argv: list[str] | None = None) -> None` via `ShellExecuteW` runas; then caller exits
- On non-Windows import of admin module in tests: mock or skip with `pytest.importorskip` / `sys.platform` guard

- [ ] **Step 1: Test is_admin returns bool (no crash)**

```python
import sys
import pytest

@pytest.mark.skipif(sys.platform != "win32", reason="Windows only")
def test_is_admin_returns_bool():
    from tempcleaner.platform_win.admin import is_admin
    assert isinstance(is_admin(), bool)
```

- [ ] **Step 2–4: Implement, pass, commit**

```powershell
git commit -am "feat(platform): detect admin and support re-elevation"
```

---

### Task 8: CLI and application entrypoint

**Files:**
- Modify: `src/tempcleaner/app.py`
- Create: `tests/test_cli.py`

**Interfaces:**
- `main(argv: list[str] | None = None) -> int`
- argparse:
  - no args → GUI (`run_gui()`)
  - `--version`
  - `--scan` / `--dry-run` / `--clean` (mutually exclusive group with GUI default)
  - `--targets id,id` optional
  - `--yes` required for `--clean`
  - `--scheduled` headless clean using settings scheduled targets
- Exit codes: `0` ok, `1` error, `2` bad usage

- [ ] **Step 1: CLI tests**

```python
from tempcleaner.app import main

def test_version_exit_zero(capsys):
    assert main(["--version"]) == 0
    assert "2.0.0" in capsys.readouterr().out
```

For clean without `--yes`:
```python
def test_clean_requires_yes():
    assert main(["--clean"]) == 2
```

- [ ] **Step 2: Implement argparse + wire engine for headless modes; GUI stub `run_gui()` opens placeholder window or imports ui (Task 9 fills UI)**

Until UI exists, `run_gui()` can open a minimal Tk window titled "TempCleaner" so `-m tempcleaner` works, replaced in Task 9.

- [ ] **Step 3: Pass tests, manual smoke**

```powershell
python -m tempcleaner --version
python -m tempcleaner --help
```

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: add CLI entrypoint for scan, dry-run, clean, scheduled"
```

---

### Task 9: UI shell — main window, Clean tab, worker thread

**Files:**
- Create: `src/tempcleaner/ui/__init__.py`, `src/tempcleaner/ui/main_window.py`, `src/tempcleaner/ui/components.py`, `src/tempcleaner/ui/dialogs.py`

**Interfaces:**
- `run_gui() -> None` — builds `ttk` main window, notebook, status bar, admin badge
- Clean tab: checkboxes for targets (filter advanced unless settings allow), Scan / Dry-run / Clean buttons, progress, cancel
- Background: `threading.Thread` runs engine; UI updates via `root.after`
- Track `last_dry_run_signature: frozenset[str] | None` for require-dry-run gate
- Clean button opens `confirm_delete_dialog(...)` before `engine.clean(..., confirmed=True)`

**Confirm dialog behavior:**
- Shows target names, total size if known, permanent delete warning
- Checkbox “I understand files will be permanently deleted.”
- Default button Cancel; Delete disabled until checked

- [ ] **Step 1: Implement UI modules (manual test — no pytest GUI required)**

- [ ] **Step 2: Manual verification checklist**

```text
1. python -m tempcleaner
2. Window opens with tabs
3. Admin badge shows Elevated or Standard user
4. Default targets checked per defaults
5. Scan populates summary without deleting
6. Dry-run works
7. Clean without dry-run blocked if setting on
8. Confirm dialog cancels safely
```

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat(ui): add main window, Clean tab, and confirm dialog"
```

---

### Task 10: Results, Settings, Logs tabs

**Files:**
- Create: `src/tempcleaner/ui/results_view.py`, `src/tempcleaner/ui/settings_view.py`, `src/tempcleaner/ui/logs_view.py`
- Modify: `src/tempcleaner/ui/main_window.py`

**Interfaces:**
- Results: ttk.Treeview columns Target, Action, Found, Deleted, Skipped, Failed, Bytes; export to JSON/TXT via `filedialog`
- Settings: toggles bound to `SettingsStore`; Save applies immediately or on button
- Logs: read tail of current log file (last ~200 lines), Refresh, Open folder

- [ ] **Step 1: Implement views and wire into notebook**

- [ ] **Step 2: Manual test settings persistence (restart app, values stick)**

- [ ] **Step 3: Commit**

```powershell
git commit -am "feat(ui): add Results, Settings, and Logs tabs"
```

---

### Task 11: Task Scheduler integration + Schedule tab

**Files:**
- Create: `src/tempcleaner/platform_win/scheduler.py`, `src/tempcleaner/ui/schedule_view.py`, `tests/test_scheduler.py`
- Modify: `main_window.py`, settings keys already defined

**Interfaces:**
- `TASK_NAME = "TempCleaner Scheduled Clean"`
- `install_schedule(frequency: str, time_hhmm: str, weekday: str | None, command: str) -> None`
- `remove_schedule() -> None`
- `schedule_exists() -> bool`
- Implementation: `subprocess.run(["schtasks", ...], capture_output=True, text=True, check=False)` and raise `RuntimeError` with stderr on failure
- Command line example:
  `py -3 -m tempcleaner --scheduled` or path to EXE when frozen (`getattr(sys, 'frozen', False)`)
- Schedule tab: enable, frequency, time, apply/remove, status label
- `--scheduled` path in `app.py`: load settings; if not enabled, log and exit 0; filter targets by scheduled list and settings flags; `engine.clean(..., confirmed=True)` (confirmation waived only in scheduled/CLI with explicit modes — CLI still needs `--yes`; scheduled is the second trusted path and logs heavily)

- [ ] **Step 1: Unit-test command builder (pure function)**

```python
from tempcleaner.platform_win.scheduler import build_schtasks_create_args

def test_build_daily_args():
    args = build_schtasks_create_args(
        task_name="TempCleaner Scheduled Clean",
        frequency="daily",
        time_hhmm="03:00",
        weekday=None,
        command='C:\\Python\\python.exe -m tempcleaner --scheduled',
    )
    assert "schtasks" in args[0] or args[0].endswith("schtasks")
    assert "/TN" in args
```

Implement `build_schtasks_create_args` returning full argv list for easy testing without creating real tasks in CI.

- [ ] **Step 2: Implement install/remove using builder**

- [ ] **Step 3: Manual test create/remove on dev machine (user approval if destructive — schtasks only)**

- [ ] **Step 4: Commit**

```powershell
git commit -am "feat: Windows Task Scheduler integration and Schedule tab"
```

---

### Task 12: Update check

**Files:**
- Create: `src/tempcleaner/platform_win/updates.py`, `tests/test_updates.py`
- Modify: Settings + About/main window startup

**Interfaces:**
- `check_latest_release(current: str, url: str = "https://api.github.com/repos/Rulesmash/TempCleaner/releases/latest", timeout: float = 5.0) -> tuple[bool, str | None, str | None]`
  - Returns `(update_available, latest_tag, html_url)`
  - On network error: `(False, None, None)` and log warning — never crash
- Parse tag `v2.0.1` vs `2.0.0` with simple tuple comparison of numeric parts
- UI: button “Check for updates”; optional startup check if setting enabled

- [ ] **Step 1: Test version compare helper with mocked urllib**

```python
from tempcleaner.platform_win.updates import version_tuple, is_newer

def test_is_newer():
    assert is_newer("2.0.1", "2.0.0") is True
    assert is_newer("2.0.0", "2.0.0") is False
    assert is_newer("1.9.9", "2.0.0") is False
```

- [ ] **Step 2: Implement, pass, wire UI, commit**

```powershell
git commit -am "feat: optional GitHub Releases update check"
```

---

### Task 13: Remove legacy 1.x modules and clean assets

**Files:**
- Delete: `main.py`, `Deleter.py`, `local_temp.py`, `percent_temp.py`, `prefetch.py` (repo root legacy)
- Delete or move obsolete `assets/button_1.png`, `image_*.png` if unused
- Keep `maicon.ico` / app icon under `assets/`
- Update any leftover imports

- [ ] **Step 1: Ensure `python -m tempcleaner` still works**

- [ ] **Step 2: Delete legacy files**

- [ ] **Step 3: Commit**

```powershell
git commit -am "chore: remove TempCleaner 1.x modules and obsolete UI assets"
```

---

### Task 14: Documentation suite

**Files:**
- Create/overwrite: `README.md`, `CHANGELOG.md`, `CONTRIBUTING.md`, `SECURITY.md`, `docs/user-guide.md`, `docs/admin-elevation.md`, `docs/packaging.md`

**README must include:** badges/metadata, overview, safety disclaimer (permanent delete), requirements, install from source, GUI/CLI usage, targets table, scheduling, building EXE, contributing, license, support link.

**CHANGELOG:** `## [2.0.0] - YYYY-MM-DD` with Breaking Changes and Added sections matching the spec.

- [ ] **Step 1: Write all docs to match implemented behavior (no aspirational features)**

- [ ] **Step 2: Commit**

```powershell
git commit -am "docs: add industry-standard README, guides, changelog, security"
```

---

### Task 15: CI, dev scripts, packaging script

**Files:**
- Create: `.github/workflows/ci.yml`, `scripts/install_dev.ps1`, `scripts/build_exe.ps1`, `.github/ISSUE_TEMPLATE/bug_report.md` (optional short template)

**CI workflow:**
```yaml
name: ci
on:
  push:
    branches: [main]
  pull_request:
jobs:
  test:
    runs-on: windows-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.12"]
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python-version }}
      - name: Install
        run: python -m pip install -U pip && pip install -e ".[dev]"
      - name: Ruff
        run: ruff check src tests
      - name: Pytest
        run: pytest -q
```

**build_exe.ps1:** activate venv if present; `pyinstaller --noconfirm --windowed --name TempCleaner --icon assets/maicon.ico -m tempcleaner` (adjust module entry as needed); document output under `dist/`.

- [ ] **Step 1: Add workflow and scripts**

- [ ] **Step 2: Run locally**

```powershell
ruff check src tests
pytest -q
```

- [ ] **Step 3: Commit**

```powershell
git commit -am "ci: Windows GitHub Actions and packaging/dev scripts"
```

---

### Task 16: Full verification, push main, delete TestA, tag

**Files:** none new (release process)

- [ ] **Step 1: Full local verification**

```powershell
ruff check src tests
pytest -q
python -m tempcleaner --version
python -m tempcleaner --scan --targets user_temp
# GUI smoke manually
```

- [ ] **Step 2: Push main (network; requires user-approved credentials)**

```powershell
git push -u origin main
```

Do **not** `--force` unless user explicitly requests history rewrite.

- [ ] **Step 3: Delete remote TestA**

```powershell
git push origin --delete TestA
```

- [ ] **Step 4: Tag and push tag when release artifacts ready**

```powershell
git tag -a v2.0.0 -m "TempCleaner 2.0.0"
git push origin v2.0.0
```

Optional: run `scripts/build_exe.ps1` and attach to GitHub Release via `gh` or web UI.

- [ ] **Step 5: Final commit only if verification fixed issues; otherwise done**

---

## Spec coverage checklist (plan self-review)

| Spec item | Task(s) |
|-----------|---------|
| Modular `src/tempcleaner` layout | 1 |
| Models + safety allowlists | 2 |
| Expanded targets + defaults | 3 |
| Scan / dry-run / clean engine | 4 |
| Settings JSON AppData | 5 |
| Logging + sizes | 6 |
| Admin detect/elevate | 7 |
| CLI + entrypoints | 8 |
| Modern ttk UI Clean + confirm | 9 |
| Results / Settings / Logs | 10 |
| Schedule + schtasks + `--scheduled` | 11 |
| Update check | 12 |
| Remove 1.x code | 13 |
| Industry docs | 14 |
| CI + gitignore + packaging scripts | 1, 15 |
| Push main, delete TestA, tag v2.0.0 | 16 |
| No tray / no Recycle Bin / no browser caches | Explicit non-goals — not implemented |
| Tests never touch real Windows dirs | 4 (tmp_path), global constraint |

**Type consistency notes:**
- Target IDs are snake_case strings listed in Task 3.
- `CleanEngine.clean(..., confirmed: bool)` is the single gate; GUI sets `True` only after dialog; CLI requires `--yes`; `--scheduled` uses `confirmed=True` after settings enable check.
- `SettingsStore.load() -> dict` uses keys from Task 5 everywhere in UI/CLI.

**Placeholder scan:** none intentional; implementation may adjust PyInstaller flags slightly but must keep windowed EXE + icon.

---

## Execution handoff

Plan complete and saved to `docs/superpowers/plans/2026-08-03-tempcleaner-v2-revamp.md`.

**Two execution options:**

1. **Subagent-Driven (recommended)** — Fresh subagent per task, review between tasks, fast iteration (`subagent-driven-development`).
2. **Inline Execution** — Execute tasks in this session with checkpoints (`executing-plans`).

Which approach do you want?
