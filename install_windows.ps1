$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "Installing RoomSentry Local v1.4..." -ForegroundColor Green

if (!(Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python was not found. Install Python 3.10+ from python.org, tick 'Add Python to PATH', then rerun this." -ForegroundColor Red
    exit 1
}

if (!(Test-Path "venv")) {
    python -m venv venv
}

. .\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python migrate_config.py
New-Item -ItemType Directory -Force -Path snapshots, logs, events, clips, runtime | Out-Null

Write-Host ""
Write-Host "Install complete." -ForegroundColor Green
Write-Host "Run: .\run_windows.ps1 or double-click START_ROOM_SENTRY.bat"
Write-Host "Settings: .\settings_windows.ps1 or double-click SETTINGS.bat"
Write-Host "Live dashboard: double-click START_DASHBOARD_SERVER.bat or START_ROOM_SENTRY_AND_DASHBOARD.bat"
