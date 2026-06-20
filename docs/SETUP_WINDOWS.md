# Windows Setup

## 1. Install Python

Install Python 3.10 or newer from python.org or the Microsoft Store. During install, enable **Add Python to PATH** if shown.

Check:

```powershell
python --version
```

## 2. Allow local scripts

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
```

## 3. Install RoomSentry dependencies

From the RoomSentry folder:

```powershell
.\install_windows.ps1
```

## 4. Create your local config

```powershell
Copy-Item config.example.json config.json
```

## 5. Run diagnostics

```powershell
python doctor.py
```

Or double-click:

```text
RUN_DOCTOR.bat
```

## 6. Start RoomSentry

Best option:

```text
START_ROOM_SENTRY_AND_DASHBOARD.bat
```

Dashboard:

```text
http://127.0.0.1:8765
```
