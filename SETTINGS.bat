@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File "%~dp0settings_windows.ps1"
pause
