# Admin elevation (TempCleaner 2.0)

## Why elevation exists

Some clean targets live under protected system paths. Without administrator rights, listing or deleting children often fails with `PermissionError` / access denied. TempCleaner **detects** elevation and can **relaunch** elevated via Windows UAC. It does **not** silently escalate mid-delete for individual files.

## How detection works

- API: `shell32.IsUserAnAdmin()` via `ctypes` (`tempcleaner.platform_win.admin.is_admin`).
- On API failure, the app treats the process as **not** admin.
- The GUI shows an admin badge and a **Restart as admin** control when not elevated.

## How relaunch works

- `relaunch_as_admin()` calls `ShellExecuteW` with the `runas` verb (UAC prompt).
- **Interpreter runs:** elevated process is `python.exe` with the same script/module arguments.
- **Frozen EXE (PyInstaller):** elevated process is the EXE; remaining CLI args are preserved.
- The caller should exit after a successful relaunch so only the elevated instance remains.
- If the user cancels UAC (or ShellExecute fails), an `OSError` is raised and the original process continues un-elevated.

## Which targets typically need admin

| Target ID | Requires admin (registry flag) | Notes |
|-----------|--------------------------------|-------|
| `user_temp` | No | User-writable TEMP |
| `windows_temp` | Yes | Often needs elevation to list/delete |
| `prefetch` | Yes | System Prefetch folder |
| `recent` | No | Per-user Recent folder |
| `thumbcache` | No | Per-user Explorer caches (may still be locked) |
| `delivery_optimization` | Yes | Service profile cache paths |
| `windows_update_download` | Yes | Under `SoftwareDistribution` |

“Requires admin” means the product expects elevation for reliable success — not that every machine always blocks non-admin access the same way. Non-elevated runs still **attempt** operations and **report** failures clearly.

## GUI behavior

1. Select elevated/advanced targets while not admin.
2. Starting Clean may prompt to restart as admin or adjust selection (deselect elevated targets).
3. **Restart as admin** triggers UAC; accept to continue elevated.
4. After elevation, re-run scan/dry-run/clean as needed.

## CLI behavior

- There is **no** automatic UAC prompt for CLI.
- Run an elevated terminal (or elevated EXE) when cleaning elevated targets:

```powershell
# From an elevated PowerShell / CMD
python -m tempcleaner --dry-run --targets windows_temp,prefetch
python -m tempcleaner --clean --yes --targets windows_temp,prefetch
```

## Scheduled tasks

- Task name: **`TempCleaner Scheduled Clean`**.
- The task runs `python -m tempcleaner --scheduled` or `TempCleaner.exe --scheduled`.
- Task Scheduler’s own “Run with highest privileges” setting is controlled when you create/edit the task (TempCleaner’s `schtasks /Create` helper uses the command + schedule parameters it builds; review the task in Task Scheduler if elevated system cleans fail in logs).
- Headless scheduled cleans **do not** show a UAC dialog at fire time. If the task runs unelevated, elevated targets will fail/skip with log entries.
- Prefetch on a schedule is **opt-in** (`allow_prefetch_scheduled`).

## Safety notes when elevated

- Elevation increases blast radius: system caches become deletable.
- Deletes remain **permanent** (no Recycle Bin).
- Path allowlists still apply; elevation does not unlock arbitrary filesystem wipe.
- Prefer dry-run while elevated before first real clean of Prefetch or Windows Update downloads.

## Troubleshooting

| Issue | Mitigation |
|-------|------------|
| UAC cancelled | Stay unelevated; deselect elevated targets or try again |
| Prefetch empty/errors without admin | Expected; elevate and retry |
| Scheduled elevated clean fails | Edit task to run with highest privileges / admin account; check logs |
| “Restart as admin” no new window | Check antivirus/UAC policy; inspect log for ShellExecute error codes |

## Related code

- `src/tempcleaner/platform_win/admin.py` — `is_admin`, `relaunch_as_admin`
- `src/tempcleaner/ui/main_window.py` — badge, relaunch, clean-time admin prompt
- `src/tempcleaner/core/targets.py` — `requires_admin` flags per target
