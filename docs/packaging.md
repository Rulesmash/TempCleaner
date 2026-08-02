# Packaging TempCleaner (EXE)

TempCleaner 2.0 runs from source with **no third-party runtime dependencies**. For end users who do not install Python, build a **standalone Windows executable** with **PyInstaller** (dev dependency only).

## Prerequisites

| Item | Notes |
|------|--------|
| OS | Windows (build on Windows for Windows) |
| Python | 3.10+ matching your support matrix |
| Repo checkout | Project root with `pyproject.toml` and `src/tempcleaner/` |
| Icon | `assets/maicon.ico` |
| Dev install | `pip install -e ".[dev]"` (pulls `pyinstaller`) |

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e ".[dev]"
```

Optional helper scripts (added with CI/packaging task when present):

- `scripts/install_dev.ps1` — create venv + install editable with `[dev]`
- `scripts/build_exe.ps1` — wrap the PyInstaller invocation below

If those scripts are not in the tree yet, use the manual commands in this document.

## Recommended PyInstaller command

From the **repository root**:

```powershell
pyinstaller `
  --noconfirm `
  --windowed `
  --name TempCleaner `
  --icon assets\maicon.ico `
  -m tempcleaner
```

| Flag | Purpose |
|------|---------|
| `--noconfirm` | Overwrite previous build output without prompts |
| `--windowed` | No console window for GUI use (GUI default path) |
| `--name TempCleaner` | Output base name |
| `--icon assets\maicon.ico` | Window/EXE icon |
| `-m tempcleaner` | Entry via the `tempcleaner` package (`__main__` / app) |

### Output locations

| Path | Content |
|------|---------|
| `dist/TempCleaner.exe` (or `dist/TempCleaner/…` depending on onedir/onefile default) | Distributable artifact |
| `build/` | Intermediate build files (safe to delete) |
| `*.spec` | Generated spec (often gitignored) |

Exact layout depends on PyInstaller version and whether you switch to `--onefile` vs onedir. Prefer documenting whatever `scripts/build_exe.ps1` standardizes when that script exists.

### Onefile example (optional)

```powershell
pyinstaller --noconfirm --windowed --onefile --name TempCleaner --icon assets\maicon.ico -m tempcleaner
```

Onefile starts slower (self-extract) but is easier to zip for GitHub Releases.

## CLI on a windowed EXE

`--windowed` hides the console. For headless use (`--scan`, `--clean --yes`, `--scheduled`), either:

1. Build a second **console** binary for automation, or  
2. Use a console-subsystem build for release if you rely heavily on CLI stdout, or  
3. Rely on log files under `%AppData%\TempCleaner\logs\` for scheduled runs.

Frozen detection in code:

- `sys.frozen` is set under PyInstaller.
- Scheduled command becomes `"C:\path\TempCleaner.exe" --scheduled`.
- Elevation relaunch uses the EXE path and remaining argv.

## What to ship

Minimum release package:

1. `TempCleaner.exe` (or onedir folder)
2. Link to [LICENSE](../LICENSE) (GPLv3) — include `LICENSE` text in the release zip when practical
3. Short usage notes / link to README safety section (permanent delete)

Optional:

- `CHANGELOG.md` excerpt for the release tag
- SHA256 checksums for the artifact

## GitHub Releases

1. Tag when ready: `v2.0.0` (and matching version in `pyproject.toml` / `version.py`).
2. Attach the EXE or zip built on a clean Windows machine.
3. Release notes should state:
   - Permanent delete (no Recycle Bin)
   - Windows only
   - Confirm / `--yes` requirements
   - No tray / no soft-delete

Update checks (if enabled by the user) query:

`https://api.github.com/repos/Rulesmash/TempCleaner/releases/latest`

Packaging does **not** implement auto-download of that release.

## Smoke test after build

On a Windows 10/11 machine:

```powershell
.\dist\TempCleaner.exe --version
# Expect: TempCleaner 2.0.0  (console build) or check GUI About / logs if fully windowed

# If you have a console build or can attach a console:
.\dist\TempCleaner.exe --scan --targets user_temp
```

GUI smoke:

1. Launch EXE → Clean tab visible.
2. Dry-run User Temp → Results populate.
3. Confirm dialog appears before clean; Cancel works.
4. Logs appear under `%AppData%\TempCleaner\logs\`.

## CI note

GitHub Actions (when configured) runs **ruff + pytest** on `windows-latest`. Building and attaching the EXE is typically a release-time step, not required for every PR, unless you add a dedicated packaging job.

## Non-goals for 2.0 packaging

- Inno Setup / NSIS installer as a hard requirement (optional follow-up)
- Code signing (recommended for public trust, not implemented in-repo by default)
- Auto-update that downloads and replaces the EXE

## Related

- [README — Building an EXE](../README.md#building-an-exe)
- [User guide](user-guide.md)
- [Admin elevation (frozen EXE)](admin-elevation.md)
- Dev dependency: `pyinstaller>=6.0` in `pyproject.toml` optional `[dev]`
