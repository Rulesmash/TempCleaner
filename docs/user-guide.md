# TempCleaner User Guide (v2.0.0)

This guide describes **actual** TempCleaner 2.0 behavior on Windows.

## Table of contents

1. [What it does](#what-it-does)
2. [Safety first](#safety-first)
3. [Install and start](#install-and-start)
4. [GUI walkthrough](#gui-walkthrough)
5. [CLI reference](#cli-reference)
6. [Targets](#targets)
7. [Settings](#settings)
8. [Scheduling](#scheduling)
9. [Logs and data files](#logs-and-data-files)
10. [Updates](#updates)
11. [Troubleshooting](#troubleshooting)
12. [What 2.0 does not include](#what-20-does-not-include)

---

## What it does

TempCleaner measures and can **permanently delete** contents of common Windows temporary and cache locations. You choose which targets to run, optionally dry-run first, then confirm before a real clean (GUI) or pass `--yes` (CLI).

Default targets on a fresh install: **User Temp** and **Windows Temp**.

---

## Safety first

| Rule | Behavior in 2.0 |
|------|-----------------|
| Permanent delete | Files are removed permanently |
| Recycle Bin | **Not used** |
| GUI confirm | Modal dialog + “I understand files will be permanently deleted.” |
| Dry-run gate | By default, GUI clean is blocked until you dry-run the current selection this session |
| CLI | `--clean` without `--yes` exits with a usage error |
| Path safety | Only allowlisted roots; refuses drive roots and the user profile root |
| Errors | Locked / denied paths are skipped and reported — not silently ignored as “full success” |

**Recommendation:** Scan → Dry-run → review Results → Clean.

---

## Install and start

### From source

```powershell
pip install -e .
python -m tempcleaner
```

Requires **Python 3.10+** on **Windows**. On non-Windows, the app prints that it supports Windows only and exits.

### Built EXE

If you have a packaged `TempCleaner.exe` (see [packaging.md](packaging.md)), run it like any Windows app. CLI flags still work:

```powershell
.\TempCleaner.exe --version
.\TempCleaner.exe --scan
```

---

## GUI walkthrough

### Shell

- Native **ttk** window (no PNG button strip).
- Top bar: title, admin badge, **Restart as admin**.
- Tabs: **Clean** | **Results** | **Schedule** | **Settings** | **Logs**.
- Status bar shows last action / busy state.

### Clean tab

1. Check the targets you want (risk tags: Safe / Elevated / Advanced).
2. Use helpers if available (e.g. select defaults / safe).
3. **Scan** — counts files/dirs and sizes; no deletes.
4. **Dry-run** — same measurement path as scan; no deletes; typically switches focus to Results.
5. **Clean…** — after dry-run gate (if enabled) and admin checks:
   - Confirm dialog lists targets and size when known.
   - Default focus is **Cancel**.
   - **Delete permanently** stays disabled until you check the acknowledgment box.
6. **Cancel** during a running operation requests cooperative cancel between items.

Advanced targets stay unavailable until **Allow advanced targets** is enabled in Settings.

### Results tab

- Table of the last engine report: found / deleted / skipped / failed / bytes.
- Error samples for failures.
- **Export JSON…** and **Export TXT…**.

### Schedule tab

See [Scheduling](#scheduling).

### Settings tab

See [Settings](#settings). Open logs/settings folders and reset defaults from here.

### Logs tab

- Tail of the current log file; refresh; open in Notepad.

### Close behavior

- By default, closing the window exits the app.
- Optional **Close minimizes**: minimizes to the **taskbar** only. There is **no system tray icon** in 2.0.

---

## CLI reference

```text
python -m tempcleaner [options]
```

| Mode | Command | Deletes? |
|------|---------|----------|
| GUI | (no mode flag) | Only after GUI confirm |
| Scan | `--scan` | No |
| Dry-run | `--dry-run` | No |
| Clean | `--clean --yes` | **Yes (permanent)** |
| Scheduled | `--scheduled` | **Yes**, if enabled in settings |
| Version | `--version` | No |

Common options:

| Option | Description |
|--------|-------------|
| `--targets id,id` | Explicit target IDs. If omitted, uses `selected_targets` from settings (or defaults). |
| `--yes` | Required with `--clean` to confirm permanent deletion. |

Examples:

```powershell
python -m tempcleaner --dry-run --targets user_temp,recent
python -m tempcleaner --clean --yes --targets user_temp
```

Exit codes: `0` OK, `1` error/cancel, `2` bad usage.

---

## Targets

| ID | Description | Admin | Default | Risk |
|----|-------------|-------|---------|------|
| `user_temp` | Current user’s TEMP directory | No | On | Safe |
| `windows_temp` | `C:\Windows\Temp` | Usually | On | Elevated |
| `prefetch` | Prefetch cache (first launches may be slower after clean) | Yes | Off | Elevated |
| `recent` | Recent documents / jump-list shortcuts | No | Off | Safe |
| `thumbcache` | Explorer `thumbcache_*.db` / `iconcache_*.db` | No | Off | Safe |
| `delivery_optimization` | Delivery Optimization download cache | Often | Off | Elevated |
| `windows_update_download` | `SoftwareDistribution\Download` | Yes | Off | Advanced |

Only **children** of each target root are removed (subject to name filters for thumbcache). The engine does not wipe arbitrary folders you type in — there is no custom-path feature in 2.0.

---

## Settings

Stored at: `%AppData%\TempCleaner\settings.json`

| Key | Default | Meaning |
|-----|---------|---------|
| `selected_targets` | `user_temp`, `windows_temp` | Last / preferred GUI selection |
| `require_dry_run_before_clean` | `true` | GUI must dry-run before clean |
| `allow_advanced_targets` | `false` | Unlock advanced risk targets |
| `allow_prefetch_scheduled` | `false` | Allow Prefetch on scheduled runs |
| `scheduled_clean_enabled` | `false` | Headless schedule may clean |
| `scheduled_targets` | `[]` | Targets used by `--scheduled` |
| `schedule_frequency` | `daily` | `daily` or `weekly` |
| `schedule_time` | `03:00` | 24-hour `HH:MM` |
| `schedule_weekday` | `MON` | Used when weekly |
| `close_minimizes` | `false` | Close → minimize to taskbar |
| `check_updates_on_startup` | `false` | Optional GitHub latest-release check |
| `log_level` | `INFO` | Logging level |

---

## Scheduling

1. Select targets on the **Clean** tab.
2. Open **Schedule**, enable scheduled clean, set frequency/time (and weekday if weekly).
3. **Apply** — installs/replaces Task Scheduler task **`TempCleaner Scheduled Clean`** and saves `scheduled_targets` from the current Clean selection.
4. **Remove** deletes the task (idempotent if already missing).

Runtime command:

- Source install: `python.exe -m tempcleaner --scheduled`
- Frozen EXE: `TempCleaner.exe --scheduled`

Scheduled rules:

- Does nothing if `scheduled_clean_enabled` is false.
- Skips advanced targets unless allowed.
- Skips Prefetch unless `allow_prefetch_scheduled` is true.
- No GUI confirm — confirmation is the act of enabling the schedule; all work is logged.
- Elevated targets may fail if the task does not run with sufficient rights (see [admin-elevation.md](admin-elevation.md)).

---

## Logs and data files

| Item | Location |
|------|----------|
| Settings | `%AppData%\TempCleaner\settings.json` |
| Logs | `%AppData%\TempCleaner\logs\tempcleaner-YYYYMMDD.log` |

Logs record scans, cleans, skips, elevation/schedule actions, and update-check outcomes.

---

## Updates

Optional check against GitHub Releases for [Rulesmash/TempCleaner](https://github.com/Rulesmash/TempCleaner):

- **Does not** auto-download or auto-install.
- May show that a newer tag exists and a release URL.
- Startup check is **off** by default; you can run check-from-settings when available.

---

## Troubleshooting

| Symptom | What to try |
|---------|-------------|
| Prefetch / Windows Temp fails | Restart as admin; re-run clean |
| “--clean requires --yes” | Add `--yes` only after reviewing `--dry-run` |
| Clean button blocked (GUI) | Run **Dry-run** first if require-dry-run is on |
| Advanced target missing | Enable **Allow advanced targets** in Settings |
| Scheduled task did nothing | Confirm enable flag, targets list, and logs for that day |
| Partial deletes | Normal for locked files; read Results / log errors |
| Non-Windows | Unsupported — app refuses to start |

---

## What 2.0 does not include

- System tray icon  
- Recycle Bin recovery  
- Browser cache cleaners  
- Custom user-defined paths  
- Auto-update installers  
- Polished third-party setup.exe as a hard requirement  

See the [README](../README.md) and [design spec](superpowers/specs/2026-08-03-tempcleaner-v2-revamp-design.md) for product scope.
