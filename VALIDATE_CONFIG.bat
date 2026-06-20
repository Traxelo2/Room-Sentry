@echo off
cd /d "%~dp0"
powershell -ExecutionPolicy Bypass -File .\validate_config_windows.ps1
pause
