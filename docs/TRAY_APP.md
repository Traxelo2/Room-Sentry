# Windows Tray App

RoomSentry v1.7 adds an optional Windows system tray controller.

## What it does

- Starts `room_sentry.py` and `dashboard_server.py` for you.
- Adds a tray icon with quick actions.
- Opens the dashboard from the tray.
- Queues local commands without exposing the dashboard publicly.

## Start it

Double-click:

```text
START_ROOM_SENTRY_TRAY.bat
```

The tray menu includes:

- Open dashboard
- Arm
- Disarm
- Take snapshot
- Reload config
- Start RoomSentry
- Start dashboard server
- Quit RoomSentry + tray

## Start with Windows

Double-click:

```text
CREATE_TRAY_STARTUP_SHORTCUT.bat
```

To remove it:

```text
REMOVE_TRAY_STARTUP_SHORTCUT.bat
```

## Dependencies

Tray mode uses:

```text
pystray
pillow
```

These are included in `requirements.txt`. Run `install_windows.ps1` again if the tray app says they are missing.

## Privacy note

The tray app only writes command files into the local `runtime/` folder and opens the local dashboard URL. It does not send camera data anywhere.
