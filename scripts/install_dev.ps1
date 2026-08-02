# Install TempCleaner in editable mode with [dev] extras (pytest, ruff, pyinstaller).
# Run from anywhere; resolves the repository root as the parent of scripts/.
# Usage: powershell -ExecutionPolicy Bypass -File scripts\install_dev.ps1

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
Set-Location $RepoRoot

Write-Host "Repository root: $RepoRoot"

$VenvPath = Join-Path $RepoRoot ".venv"
$ActivatePs1 = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $ActivatePs1)) {
    Write-Host "Creating virtual environment at .venv ..."
    python -m venv $VenvPath
    if ($LASTEXITCODE -ne 0) {
        throw "python -m venv failed with exit code $LASTEXITCODE"
    }
}

Write-Host "Activating .venv ..."
. $ActivatePs1

Write-Host "Upgrading pip ..."
python -m pip install -U pip
if ($LASTEXITCODE -ne 0) {
    throw "pip upgrade failed with exit code $LASTEXITCODE"
}

Write-Host "Installing package editable with [dev] ..."
pip install -e ".[dev]"
if ($LASTEXITCODE -ne 0) {
    throw "pip install -e `".[dev]`" failed with exit code $LASTEXITCODE"
}

Write-Host ""
Write-Host "Dev install complete."
Write-Host "  ruff check src tests"
Write-Host "  pytest -q"
Write-Host "  python -m tempcleaner --version"
Write-Host "  scripts\build_exe.ps1   # package EXE (optional)"
