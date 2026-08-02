# Build a windowed TempCleaner.exe with PyInstaller.
# Prefer an existing .venv (created by scripts/install_dev.ps1); falls back to PATH.
# Run from anywhere; resolves the repository root as the parent of scripts/.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\build_exe.ps1
#
# Output:
#   dist\TempCleaner.exe   (or dist\TempCleaner\... for onedir layouts)
# Intermediate:
#   build\                 (safe to delete)
#   TempCleaner.spec       (generated; often gitignored)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "Repository root: $RepoRoot"

$Icon = Join-Path $RepoRoot "assets\maicon.ico"
if (-not (Test-Path $Icon)) {
    throw "Icon not found: $Icon"
}

$VenvActivate = Join-Path $RepoRoot ".venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "Activating .venv ..."
    . $VenvActivate
} else {
    Write-Host "No .venv found; using current Python environment."
}

# Prefer the active interpreter's module form (avoids stale PATH shims).
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
& python -c "import PyInstaller" 1>$null 2>$null
$piExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($piExit -ne 0) {
    throw "PyInstaller not found for this Python. Run scripts\install_dev.ps1 or: pip install -e `".[dev]`""
}

# GUI ships with tkinter; a broken/missing stdlib Tcl/Tk install produces a headless-only EXE.
$ErrorActionPreference = "Continue"
& python -c "import tkinter" 1>$null 2>$null
$tkExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($tkExit -ne 0) {
    throw "tkinter is not importable in this Python. Install a Python build that includes Tcl/Tk (e.g. python.org installer with tcl/tk), then recreate .venv and reinstall: scripts\install_dev.ps1"
}

# Entry script must be a real .py path. On Windows, pyinstaller CLI -m is --manifest
# (not Python module mode). Use __main__.py with --paths src so package imports resolve.
# --collect-submodules picks up deferred imports (UI, config, etc.) under tempcleaner.
Write-Host "Running PyInstaller (windowed, name=TempCleaner) ..."
$ErrorActionPreference = "Continue"
& python -m PyInstaller `
    --noconfirm `
    --windowed `
    --name TempCleaner `
    --icon assets\maicon.ico `
    --paths src `
    --collect-submodules tempcleaner `
    src\tempcleaner\__main__.py
$piBuildExit = $LASTEXITCODE
$ErrorActionPreference = $prevEap
if ($piBuildExit -ne 0) {
    throw "PyInstaller failed with exit code $piBuildExit"
}

$DistExe = Join-Path $RepoRoot "dist\TempCleaner.exe"
$DistDir = Join-Path $RepoRoot "dist\TempCleaner"
Write-Host ""
Write-Host "Build finished."
if (Test-Path $DistExe) {
    Write-Host "  EXE: $DistExe"
} elseif (Test-Path $DistDir) {
    Write-Host "  Output directory: $DistDir"
} else {
    Write-Host "  Check dist\ for artifacts."
}
Write-Host "See docs\packaging.md for smoke tests and release notes."
