# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2026-08-03

Full product revamp. Breaking UX and structure vs 1.x.

### Breaking Changes

- **Confirmations required** — GUI clean no longer deletes in one silent click. Users must complete a permanent-delete confirmation dialog (including the acknowledgment checkbox). CLI clean requires `--clean --yes`.
- **Permanent delete only** — still no Recycle Bin / soft-delete; 2.0 makes this explicit and guarded (1.x deleted permanently without confirmations).
- **Prefetch default off** — Prefetch is not selected by default and is not scheduled by default.
- **Windows-only gate** — non-Windows platforms refuse to start with a clear message.
- **Package layout** — application lives under `src/tempcleaner/`; legacy root modules (`main.py`, `Deleter.py`, `local_temp.py`, `percent_temp.py`, `prefetch.py`) and PNG button chrome are removed.
- **ttk multi-tab UI** replaces the 1.x image-button canvas UI.
- **Runtime dependency policy** — stdlib only at runtime (no third-party UI/delete packages).
- **Version ships as 2.0.0** — not a drop-in silent 1.x workflow.

### Added

- Modular architecture: `core`, `config`, `platform_win`, `ui`, `util`.
- Clean targets: `user_temp`, `windows_temp`, `prefetch`, `recent`, `thumbcache`, `delivery_optimization`, `windows_update_download` with risk levels (safe / elevated / advanced).
- Path safety: allowlisted roots; refuse drive roots and user profile root.
- Engine operations: **scan**, **dry-run**, **clean** with structured results and cooperative cancel.
- GUI tabs: Clean, Results (export JSON/TXT), Schedule, Settings, Logs.
- Confirm dialog with permanent-delete warning and “I understand…” gate; default focus Cancel.
- Setting `require_dry_run_before_clean` (default **on**).
- Admin detection and **Restart as admin** via UAC (`ShellExecuteW` runas).
- JSON settings under `%AppData%\TempCleaner\settings.json`.
- Daily file logging under `%AppData%\TempCleaner\logs\`.
- CLI: `--scan`, `--dry-run`, `--clean --yes`, `--scheduled`, `--targets`, `--version`.
- Windows Task Scheduler integration (`schtasks`) for scheduled headless cleans.
- Optional GitHub Releases update check (stdlib `urllib`; show link only; default off on startup).
- Unit tests (`pytest`) and lint (`ruff`) as dev extras; packaging via PyInstaller (dev).
- Documentation suite: README, CHANGELOG, CONTRIBUTING, SECURITY, user guide, admin elevation, packaging.

### Changed

- Delete failures (locked/permission) are skipped and logged; results report deleted / skipped / failed counts.
- Elevated/advanced targets gated by admin awareness and settings.
- Close-to-minimize is optional and taskbar-only (no system tray).

### Removed

- 1.x silent one-click delete UX without confirmation.
- Legacy root modules and PNG button layout assets.
- Any implication of Recycle Bin recovery (never supported; now documented as out of scope).

### Security

- No bare `except:` in operational paths; catch `OSError` / `PermissionError` (and related) with logging.
- No network use except optional update check; no telemetry.
- Clean requires explicit confirmation (`confirmed=True` / `--yes` / scheduled trusted path).

## [1.x]

Prior releases were informal GUI cleaners for user temp, Windows temp, and prefetch without the 2.0 guardrails, package layout, or docs set. See repository history for details.
