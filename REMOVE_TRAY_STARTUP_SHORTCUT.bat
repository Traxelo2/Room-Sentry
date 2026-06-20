@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0remove_tray_startup_shortcut_windows.ps1"
pause
