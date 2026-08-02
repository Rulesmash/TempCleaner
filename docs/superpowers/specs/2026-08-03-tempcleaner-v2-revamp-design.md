# TempCleaner v2.0 Revamp — Design Spec

**Date:** 2026-08-03  
**Status:** Approved (design sections §1–§4)  
**Repository:** [Rulesmash/TempCleaner](https://github.com/Rulesmash/TempCleaner)  
**Local root:** `d:\Docs\My Apps\TempCleaner\Release\TempCleaner`  
**License:** GNU GPLv3 (unchanged)

## 1. Summary

TempCleaner is a Windows-only utility for clearing common temporary and system cache locations. Version 1.x is a Tkinter image-button app with three hard-coded cleaners, silent permanent deletes, no admin elevation in code, no tests, and informal documentation. Branch `TestA` on GitHub is redundant after the threading merge.

**v2.0** is a full product-platform revamp:

- Modular package architecture (Approach A)
- Modern native **ttk** UI (no PNG button layout)
- Expanded clean targets with risk levels
- Industry-grade guardrails (confirm, dry-run, path validation, logging)
- Settings, scheduling (Task Scheduler), optional update check
- CLI + GUI, tests, CI, full documentation, proper git/`.gitignore`
- Minimal third-party **runtime** dependencies (stdlib only)
- Push to `main`, delete remote `TestA`, ship as **v2.0.0**

## 2. Goals and non-goals

### Goals

1. Safe, understandable permanent cleanup of Windows junk locations.
2. Clear feedback: scan / dry-run / clean results, never silent “success” on access denied.
3. Admin awareness and optional re-elevation for elevated targets.
4. Schedulable cleans via Windows Task Scheduler without heavy dependencies.
5. Maintainable codebase with unit tests and Windows CI.
6. Industry-standard docs and git hygiene.

### Non-goals (deferred past 2.0)

- Browser cache cleaners
- User-defined custom paths
- Recycle Bin / soft-delete mode
- System tray icon (would require extra deps)
- Auto-download or auto-install of updates
- Cloud sync of settings
- Full polished third-party installer (Inno/NSIS) as a hard requirement (docs + build script first; installer optional follow-up)

## 3. Decisions (locked)

| Topic | Decision |
|-------|----------|
| Scope | Full product platform |
| UI | Modern native ttk redesign |
| Delete model | Confirm + permanent delete + dry-run (no Recycle Bin in 2.0) |
| Dependencies | Minimal: runtime stdlib only; dev deps for test/lint/packaging |
| Architecture | Approach A — modular layers under `src/tempcleaner/` |
| Git home | `Release/TempCleaner` ↔ `Rulesmash/TempCleaner` |
| History | Prefer preserve GitHub history (commit v2 on top of `main`); no force-push unless explicitly requested later |
| Version | **2.0.0** (breaking UX vs 1.x) |
| Python | **3.10+** (`match`/`case` and modern typing acceptable) |
| Platform | Windows only; refuse start elsewhere |

## 4. Architecture

### 4.1 Repository layout

```text
TempCleaner/
├── pyproject.toml
├── README.md
├── LICENSE
├── CHANGELOG.md
├── CONTRIBUTING.md
├── SECURITY.md
├── .gitignore
├── .github/
│   ├── workflows/ci.yml
│   └── ISSUE_TEMPLATE/
├── docs/
│   ├── user-guide.md
│   ├── admin-elevation.md
│   ├── packaging.md
│   └── superpowers/specs/
├── scripts/
│   ├── build_exe.ps1
│   └── install_dev.ps1
├── assets/                    # icons only
├── src/tempcleaner/
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py
│   ├── version.py
│   ├── config/
│   │   ├── settings.py
│   │   └── defaults.py
│   ├── core/
│   │   ├── models.py
│   │   ├── engine.py
│   │   ├── targets.py
│   │   └── safety.py
│   ├── platform_win/
│   │   ├── admin.py
│   │   ├── paths.py
│   │   ├── scheduler.py
│   │   └── updates.py
│   ├── ui/
│   │   ├── main_window.py
│   │   ├── components.py
│   │   ├── results_view.py
│   │   ├── settings_view.py
│   │   ├── schedule_view.py
│   │   └── dialogs.py
│   └── util/
│       ├── logging_setup.py
│       └── sizing.py
└── tests/
    ├── test_engine.py
    ├── test_safety.py
    ├── test_settings.py
    └── test_targets.py
```

Legacy root modules (`main.py`, `Deleter.py`, `local_temp.py`, `percent_temp.py`, `prefetch.py`) are removed after the package works.

### 4.2 Layers

```text
UI  →  core engine  →  platform_win / util
         ↑
      config
```

- **core** must not import Tkinter.
- **platform_win** isolates Windows APIs (`ctypes` elevation, `schtasks`, path helpers) for mocking in tests.
- **UI** calls engine/settings only; displays models.
- Entry points: `python -m tempcleaner`, optional console script `tempcleaner`.

### 4.3 Runtime data

| Data | Location |
|------|----------|
| Settings | `%AppData%\TempCleaner\settings.json` |
| Logs | `%AppData%\TempCleaner\logs\tempcleaner-YYYYMMDD.log` |
| Optional last scan | `%AppData%\TempCleaner\last_scan.json` |

### 4.4 Core models (conceptual)

- **CleanTarget:** `id`, name, description, risk (`safe` | `elevated` | `advanced`), `requires_admin`, `enabled_by_default`, `allow_scheduled_default`, path resolver, allowlisted root prefixes.
- **ScanResult / CleanResult:** per-target counts (found files/dirs, bytes), deleted/skipped/failed, error samples, duration.
- **Engine:** `scan(target_ids)`, `dry_run(target_ids)`, `clean(target_ids, *, confirm_token)`, cooperative cancel between items.

## 5. Features

### 5.1 Clean targets

| ID | Source | Admin | Default on | Notes |
|----|--------|-------|------------|--------|
| `user_temp` | `%TEMP%` / user LocalAppData Temp | No | Yes | Primary user temp |
| `windows_temp` | `C:\Windows\Temp` | Usually | Yes | Skip if not listable |
| `prefetch` | `C:\Windows\Prefetch` | Yes | **Off** | May slow first app launches after clean |
| `recent` | User Recent / Jump Lists | No | Off | Shortcuts only |
| `thumbcache` | Explorer thumbnail cache under LocalAppData | No | Off | Best-effort; locks common |
| `delivery_optimization` | Delivery Optimization cache | Often | Off | May need admin |
| `windows_update_download` | `SoftwareDistribution\Download` | Yes | Off | **Advanced**; gated by settings |

Browser caches and custom folders are out of scope for 2.0.

### 5.2 Operations

1. **Scan** — measure only; no deletes.
2. **Dry-run** — same metrics presented as “would delete”; no deletes.
3. **Clean** — permanent delete only after guardrails; return structured results.
4. **Parallelism** — multiple targets may run with a small thread pool; one UI operation at a time; cancel between items.

### 5.3 Platform features

| Feature | Implementation |
|---------|----------------|
| Settings | JSON under AppData |
| Schedule | `schtasks` create/query/delete; task runs `tempcleaner --scheduled` or built EXE equivalent |
| Minimize | Optional close-to-minimize (taskbar); no tray icon in 2.0 |
| Updates | Optional GitHub Releases API check via `urllib`; show link only; no auto-download |
| Logging | Daily log files under AppData |
| CLI | `--scan`, `--dry-run`, `--clean --yes`, `--scheduled`, `--version` |

### 5.4 Scheduled mode rules

- Requires `scheduled_clean_enabled` in settings.
- Uses last saved target selection for schedule.
- Only targets with `allow_scheduled` (per settings) run; advanced/high-risk require explicit allow.
- Prefetch in scheduled runs default **off**.
- Headless: no confirm dialog; all actions logged.
- Elevated targets fail clearly in log if task is not running elevated.

## 6. Guardrails

| Guardrail | Behavior |
|-----------|----------|
| Confirm | Clean requires modal: targets, size, count, permanent-delete warning; must check “I understand…” |
| Dry-run gate | Setting `require_dry_run_before_clean` default **on**; blocks clean until dry-run this session for current selection (GUI) |
| Path validation | Refuse if path empty, not absolute, or outside target allowlist roots |
| Root protection | Never delete drive roots or user profile root |
| Admin | Detect elevation; if selection needs admin and not elevated → prompt restart as admin or deselect |
| Busy lock | Single operation; disable Clean while running |
| Errors | Catch `OSError` / `PermissionError` (and related OS errors); log path + reason; no bare `except:` |
| Logging | All scans/cleans logged |
| Network | Only optional update check; no telemetry |
| Windows gate | Non-Windows → clear message and exit |
| CLI clean | Requires `--yes` for non-interactive permanent delete |

## 7. UI / UX

### 7.1 Shell

- Resizable main window, min ~720×520.
- System ttk (no third-party theme packs).
- Top bar: title, admin badge, Restart as admin.
- Tabs: **Clean** | **Results** | **Schedule** | **Settings** | **Logs**.
- Status bar: last action, optional free space, busy text.

### 7.2 Clean tab

- Checkbox list of targets with risk tags (`Safe` / `Elevated` / `Advanced`).
- Helpers: Select all safe / Select defaults.
- Actions: Scan, Dry-run, Clean…; progress + Cancel.
- Dry-run auto-switches to Results.
- Advanced targets hidden or disabled until Settings unlock.

### 7.3 Confirm dialog

- Default focus: Cancel.
- Delete permanently disabled until acknowledgment checkbox checked.
- Enter must not trigger delete by default.

### 7.4 Results tab

- Per-target table: Found / Deleted / Skipped / Failed / Bytes freed.
- Error sample list.
- Export report (`.txt` or `.json`).

### 7.5 Schedule tab

- Enable, frequency (daily/weekly), time, apply/remove, status of registered task.
- “Use current Clean selection” when applying.

### 7.6 Settings tab

- Require dry-run before clean (default on).
- Allow advanced targets.
- Allow Prefetch in scheduled runs (default off).
- Close minimizes (optional).
- Check updates on startup (default **off**).
- Open logs / settings folders; reset defaults.

### 7.7 Logs tab

- Tail of current log; refresh; open in Notepad.

### 7.8 Assets

- App `.ico` for window/taskbar.
- Remove dependency on PNG button chrome; legacy PNGs may be deleted or moved to `assets/legacy/` then removed.

## 8. Git, CI, packaging, docs

### 8.1 Git

1. Use `Release/TempCleaner` as project root.
2. Clone or connect remote `https://github.com/Rulesmash/TempCleaner.git`.
3. Prefer: preserve history, replace tree with v2, commit on `main`.
4. Push `main` (no force-push by default).
5. Delete remote branch **`TestA`**.
6. Tag **`v2.0.0`** when release-ready.

### 8.2 `.gitignore`

Ignore: `__pycache__/`, virtualenvs, `dist/`/`build/`/egg-info, pytest/ruff/mypy caches, IDE junk, OS junk, `*.log`, local settings, built `*.exe`/`*.zip` artifacts (releases via GitHub Releases only).

### 8.3 Documentation

| File | Role |
|------|------|
| `README.md` | Product overview, install, usage, safety, links |
| `CHANGELOG.md` | Keep a Changelog; 2.0.0 breaking changes |
| `CONTRIBUTING.md` | Dev setup, tests, PR norms |
| `SECURITY.md` | Reporting; local-delete threat notes |
| `docs/user-guide.md` | Full walkthrough |
| `docs/admin-elevation.md` | Why/how elevation |
| `docs/packaging.md` | EXE build |
| This spec | Design record |

### 8.4 CI

- GitHub Actions on `windows-latest`.
- Python 3.10 and 3.12 matrix.
- Install `[dev]`, run **ruff** + **pytest**.
- No GUI E2E in initial CI; unit-test core only with `tmp_path`.

### 8.5 Packaging

- Runtime: no third-party packages required.
- Dev optional: `pytest`, `ruff`, `pyinstaller`.
- `scripts/build_exe.ps1` produces distributable EXE with icon.
- GitHub Release attaches artifacts; replace old Drive-centric messaging.

### 8.6 Testing

- Path validation, settings I/O, engine dry-run/clean on temporary directories, target registration, mocked admin/scheduler where needed.
- Never delete real `C:\Windows\*` in tests.

## 9. CLI contract

```text
python -m tempcleaner                 # GUI
python -m tempcleaner --scan
python -m tempcleaner --dry-run [--targets id,id]
python -m tempcleaner --clean --yes [--targets id,id]
python -m tempcleaner --scheduled
python -m tempcleaner --version
python -m tempcleaner --help
```

## 10. Migration from 1.x

| 1.x | 2.0 |
|-----|-----|
| Image-button UI | ttk multi-tab UI |
| Instant delete, no confirm | Confirm + dry-run gate |
| Prefetch always available, silent fail | Prefetch default off; admin prompt; logged skips |
| Three targets only | Expanded registry |
| No settings | AppData JSON settings |
| Threading only on “delete all” | Engine-level orchestration + cancel |
| Informal README | Full docs set |
| `TestA` branch | Delete after main updated |
| Drive EXE links | GitHub Releases |

Breaking: users expecting one-click silent delete must acknowledge confirmations; Prefetch not selected by default.

## 11. Implementation phases (high level)

1. Scaffold package, `pyproject.toml`, `.gitignore`, git remote wiring.
2. Core models, targets, safety, engine + unit tests.
3. Config, logging, CLI entrypoints.
4. UI shell and all tabs/dialogs.
5. Scheduler + update check.
6. Documentation + CI workflow.
7. Build script; push `main`; delete `TestA`; tag `v2.0.0` when verified.

Detailed task breakdown belongs in the implementation plan (writing-plans), not this spec.

## 12. Success criteria

- [ ] App runs on Windows 10/11 with Python 3.10+ and as a built EXE.
- [ ] Scan / dry-run / clean work for default targets with visible results and logs.
- [ ] Clean always requires confirmation in GUI; CLI clean requires `--yes`.
- [ ] Non-elevated Prefetch/system targets report failure clearly; elevation restart works.
- [ ] Settings persist; schedule create/remove works on a dev machine.
- [ ] `pytest` and `ruff` pass on Windows CI.
- [ ] README and docs match actual behavior; CHANGELOG records 2.0.0.
- [ ] Remote `TestA` removed; `main` hosts v2 source.

## 13. Risks and mitigations

| Risk | Mitigation |
|------|------------|
| Deleting locked system files | Skip + log; never claim full success |
| User deletes critical data | Confirm + dry-run default + allowlists |
| Scheduled task without admin | Document; skip elevated targets or fail in log |
| Path resolution edge cases | Central allowlist validation in `safety.py` |
| Scope creep (tray, browsers, installer) | Explicit non-goals in §2 |

## 14. Open items

None for design. Implementation plan may timebox optional Inno/NSIS installer to a follow-up PR if packaging script + zip/EXE is sufficient for 2.0.0.
