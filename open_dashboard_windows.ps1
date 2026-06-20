$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (!(Test-Path "venv")) {
    Write-Host "venv not found. Run install_windows.ps1 first." -ForegroundColor Red
    exit 1
}

. .\venv\Scripts\Activate.ps1
python open_dashboard.py
