# TempCleaner

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform: Windows](https://img.shields.io/badge/platform-Windows-0078D6.svg)](https://github.com/Rulesmash/TempCleaner)
[![Version](https://img.shields.io/badge/version-2.0.0-green.svg)](CHANGELOG.md)

**Windows temp and cache cleaner** with dry-run, confirmations, path safety, optional scheduling, and a modern ttk UI.

- **Repository:** [github.com/Rulesmash/TempCleaner](https://github.com/Rulesmash/TempCleaner)
- **License:** [GNU GPLv3](LICENSE)
- **Version:** 2.0.0

---

## Safety disclaimer (read this)

TempCleaner **permanently deletes** files and folders under allowlisted Windows temp/cache locations.

| Fact | Detail |
|------|--------|
| Delete model | **Permanent delete** only |
| Recycle Bin | **Not used** — nothing is sent to the Recycle Bin |
| Soft-delete | **Not available** in 2.0 |
| GUI clean | Requires a confirmation dialog and an **“I understand files will be permanently deleted”** checkbox |
| CLI clean | Requires **`--clean --yes`** |
| Dry-run | Supported; default setting requires a dry-run before GUI clean |

Always run **Scan** or **Dry-run** first if you are unsure what will be removed. Locked or in-use files are skipped and logged; partial cleans are reported honestly.

---

## Overview

TempCleaner v2 is a full rewrite of the 1.x image-button cleaner:

- Modular package under `src/tempcleaner/`
- Native **ttk** multi-tab UI (Clean, Results, Schedule, Settings, Logs)
- Expanded clean targets with risk levels (Safe / Elevated / Advanced)
- Path allowlists — never deletes drive roots or the user profile root
- Settings and logs under `%AppData%\TempCleaner\`
- CLI for scan / dry-run / clean / scheduled runs
- Optional Windows Task Scheduler integration
- Optional GitHub Releases update *check* (link only; no auto-download)
- **Runtime dependencies: Python standard library only**

### Not in 2.0

- System tray icon
- Recycle Bin / soft-delete mode
- Browser cache cleaners
- User-defined custom paths
- Auto-download or auto-install of updates
- Full third-party installer (EXE build docs only; see [docs/packaging.md](docs/packaging.md))

---

## Requirements

| Item | Requirement |
|------|-------------|
| OS | **Windows** only (refuses to start on other platforms) |
| Python | **3.10+** (for source / dev installs) |
| Runtime packages | **None** (stdlib only: `tkinter`/`ttk`, `ctypes`, `urllib`, `subprocess`, …) |
| Dev extras (optional) | `pytest`, `ruff`, `pyinstaller` via `pip install -e ".[dev]"` |
| Admin | Optional; needed for Prefetch, Windows Temp (often), Delivery Optimization, Windows Update downloads |

---

## Install from source

```powershell
git clone https://github.com/Rulesmash/TempCleaner.git
cd TempCleaner

python -m venv .venv
.\.venv\Scripts\Activate.ps1

python -m pip install -U pip
pip install -e .

# Optional dev tools (tests, lint, packaging)
pip install -e ".[dev]"
```

Console entry point after install: `tempcleaner`  
Module entry: `python -m tempcleaner`

---

## GUI usage

```powershell
python -m tempcleaner
# or
tempcleaner
```

1. Open the **Clean** tab and select targets (defaults: User Temp + Windows Temp).
2. Click **Scan** or **Dry-run** to measure what would be removed.
3. Review the **Results** tab (export JSON/TXT if needed).
4. Click **Clean…** — complete the confirm dialog (acknowledge permanent delete).
5. If targets need admin and you are not elevated, use **Restart as admin** (or accept the elevation prompt).

**Settings of note (defaults):**

| Setting | Default |
|---------|---------|
| Require dry-run before clean | **On** |
| Allow advanced targets | **Off** |
| Prefetch selected by default | **Off** |
| Allow Prefetch in scheduled runs | **Off** |
| Check updates on startup | **Off** |
| Close minimizes (taskbar) | **Off** (no tray) |

More detail: [docs/user-guide.md](docs/user-guide.md) · [docs/admin-elevation.md](docs/admin-elevation.md)

---

## CLI usage

```text
python -m tempcleaner                 # GUI
python -m tempcleaner --version
python -m tempcleaner --help

python -m tempcleaner --scan
python -m tempcleaner --dry-run
python -m tempcleaner --scan --targets user_temp,windows_temp
python -m tempcleaner --clean --yes
python -m tempcleaner --clean --yes --targets user_temp
python -m tempcleaner --scheduled     # headless Task Scheduler path
```

| Flag | Meaning |
|------|---------|
| `--scan` | Measure selected targets; no deletes |
| `--dry-run` | Same measurement path as scan; no deletes |
| `--clean` | **Permanent** delete; **requires `--yes`** |
| `--yes` | Confirm permanent delete for `--clean` |
| `--targets id,id` | Comma-separated target IDs (else settings / defaults) |
| `--scheduled` | Trusted headless clean using saved schedule settings |
| `--version` | Print version and exit |

**Exit codes:** `0` success, `1` error, `2` usage error (e.g. `--clean` without `--yes`).

---

## Clean targets

| ID | Name | Typical path | Admin | Default on | Risk |
|----|------|--------------|-------|------------|------|
| `user_temp` | User Temp | `%TEMP%` | No | Yes | Safe |
| `windows_temp` | Windows Temp | `C:\Windows\Temp` | Usually | Yes | Elevated |
| `prefetch` | Prefetch | `C:\Windows\Prefetch` | Yes | **No** | Elevated |
| `recent` | Recent Items | `%APPDATA%\…\Windows\Recent` | No | No | Safe |
| `thumbcache` | Thumbnail Cache | Explorer thumb/icon cache DBs under LocalAppData | No | No | Safe |
| `delivery_optimization` | Delivery Optimization | Delivery Optimization cache | Often | No | Elevated |
| `windows_update_download` | Windows Update Downloads | `SoftwareDistribution\Download` | Yes | No | **Advanced** |

**Notes:**

- Only **contents** under each allowlisted root are deleted — not drive roots, not the user profile root, and not the root folder itself as a forbidden top-level.
- Prefetch cleanup may slow the first launch of apps until Windows rebuilds the cache.
- Advanced targets stay hidden/disabled until **Allow advanced targets** is enabled in Settings.
- Thumbcache only matches `thumbcache_*.db` / `iconcache_*.db` names.

---

## Scheduling

Windows Task Scheduler integration (via `schtasks`):

- Task name: **`TempCleaner Scheduled Clean`**
- Command (interpreter): `python -m tempcleaner --scheduled`
- Command (frozen EXE): `TempCleaner.exe --scheduled`
- Frequencies: **daily** or **weekly** (with weekday)
- On Apply, the current Clean-tab selection is saved as `scheduled_targets`
- Headless clean runs only when `scheduled_clean_enabled` is true
- Prefetch is skipped on schedule unless **Allow Prefetch in scheduled runs** is on
- Advanced targets are skipped unless allowed in settings
- **No confirm dialog** on the scheduled path — all actions are logged

Configure from the **Schedule** tab in the GUI. Elevated system targets need a task/context that can access those paths (see [docs/admin-elevation.md](docs/admin-elevation.md)).

---

## Building an EXE

Packaging uses **PyInstaller** (dev dependency). Full steps: [docs/packaging.md](docs/packaging.md).

Short form (after `pip install -e ".[dev]"`):

```powershell
# Preferred: helper script (activates .venv if present)
powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1

# Or manual (from repo root). Entry must be a .py path — do not use -m
# (on Windows PyInstaller, -m is --manifest, not Python module mode).
pyinstaller --noconfirm --windowed --name TempCleaner --icon assets\maicon.ico --paths src --collect-submodules tempcleaner src\tempcleaner\__main__.py
```

Output lands under `dist/`. Runtime still needs no third-party wheels on the end-user machine.

---

## Data locations

| Data | Path |
|------|------|
| Settings | `%AppData%\TempCleaner\settings.json` |
| Logs | `%AppData%\TempCleaner\logs\tempcleaner-YYYYMMDD.log` |

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Summary:

```powershell
pip install -e ".[dev]"
ruff check src tests
pytest -q
```

PRs welcome. Keep runtime free of third-party dependencies unless the project explicitly decides otherwise.

---

## Security

See [SECURITY.md](SECURITY.md) for reporting guidance and the local-delete threat model. This app deletes files on **your** machine under documented allowlists; it does not send telemetry.

---

## License

[GNU General Public License v3.0](LICENSE) only (`GPL-3.0-only`).

---

## Support

If TempCleaner helps you, you can support development here:

**Buy me a coffee:** [buymeacoffee.com/Rulesmash](https://buymeacoffee.com/rulesmash)

Bugs and feature requests: [GitHub Issues](https://github.com/Rulesmash/TempCleaner/issues)

---

## Further reading

- [User guide](docs/user-guide.md)
- [Admin elevation](docs/admin-elevation.md)
- [Packaging](docs/packaging.md)
- [Changelog](CHANGELOG.md)
- [Design spec](docs/superpowers/specs/2026-08-03-tempcleaner-v2-revamp-design.md)
