@echo off
cd /d "%~dp0"
start "RoomSentry Dashboard" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0start_dashboard_server_windows.ps1"
timeout /t 2 /nobreak >nul
start "RoomSentry Camera" powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_windows.ps1"
