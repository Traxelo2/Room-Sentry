@echo off
cd /d "%~dp0"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe tray_app.py --open-dashboard
) else (
  python tray_app.py --open-dashboard
)
pause
