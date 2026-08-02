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

$pyinstaller = Get-Command pyinstaller -ErrorAction SilentlyContinue
if (-not $pyinstaller) {
    throw "pyinstaller not found. Run scripts\install_dev.ps1 or: pip install -e `".[dev]`""
}

Write-Host "Running PyInstaller (windowed, name=TempCleaner) ..."
pyinstaller `
    --noconfirm `
    --windowed `
    --name TempCleaner `
    --icon assets\maicon.ico `
    -m tempcleaner

if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller failed with exit code $LASTEXITCODE"
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
