# RoomSentry Local v1.8

Local-first webcam room watcher with person detection, alerts, visual zone editing, event review/search, privacy zones, a private browser dashboard, and an optional Windows tray controller.

RoomSentry is designed for your own room, your own camera, and local experimentation. It does **not** do face recognition, identity tracking, or cloud video streaming by default.

## Highlights

- Webcam/IP camera person detection with OpenCV + YOLOv8
- Local dashboard at `http://127.0.0.1:8765`
- Arm/disarm controls from the dashboard
- Event timeline, snapshot gallery, and **event review/search**
- SQLite event database + JSONL event log
- Discord, Telegram, ntfy, and generic webhook alerts
- Optional snapshot and clip recording
- Ignore zones to stop false positives
- **Privacy zones** to blur/black out parts of the frame before previews, snapshots, or clips are saved
- **Visual zone editor** for drawing ignore/privacy zones from the dashboard
- **Windows tray app** for arm/disarm, snapshots, dashboard launch, and safe quit
- **Event review tools** to mark important events, false positives, notes, and delete selected events
- Config validator and diagnostics tools
- Windows launchers and Linux scripts
- Local-only defaults

## What is new in v1.8

1. **Event Review/Search**: search and filter events directly in the dashboard.
2. **Review markers**: mark events as important or false positives.
3. **Review notes**: add a short note to any event.
4. **Selected delete**: delete selected event rows, optionally including local snapshot/clip files.
5. **Visible export**: export the current filtered event list as JSON.
6. **Daily summary**: view totals by date, event type, important events, false positives, snapshots, and clips.

See `docs/EVENT_REVIEW.md`.


## Safety and privacy

Use RoomSentry only where you have the right to place a camera. Do not secretly monitor shared/private areas. Keep the dashboard bound to `127.0.0.1` unless you fully understand the security risk.

Secrets such as bot tokens and webhooks should go in `config.json`, which is ignored by Git. Do not commit your real config.

## Quick install on Windows

Open PowerShell in this folder:

```powershell
Set-ExecutionPolicy RemoteSigned -Scope CurrentUser
.\install_windows.ps1
```

## Run on Windows

Best tray launcher:

```text
START_ROOM_SENTRY_TRAY.bat
```

Classic all-in-one launcher:

```text
START_ROOM_SENTRY_AND_DASHBOARD.bat
```

Or run separately:

```text
START_ROOM_SENTRY.bat
START_DASHBOARD_SERVER.bat
```

Open dashboard:

```text
http://127.0.0.1:8765
```

## Windows tray mode

The tray app gives you right-click controls for arm/disarm, snapshots, opening the dashboard, and quitting safely. See `docs/TRAY_APP.md`.

To start tray mode with Windows, double-click:

```text
CREATE_TRAY_STARTUP_SHORTCUT.bat
```

To remove it:

```text
REMOVE_TRAY_STARTUP_SHORTCUT.bat
```

## Validate and diagnose

```text
VALIDATE_CONFIG.bat
RUN_DOCTOR.bat
```

From terminal:

```bash
python validate_config.py
python doctor.py
python doctor.py --camera
```


## Visual zone editor

Start the app and dashboard, wait for a camera preview, then use **Visual Zone Editor** below the preview. Pick `Ignore zone` or `Privacy zone`, drag a box, then click **Save Zones**.

The editor writes normalized coordinates to `config.json`, creates a config backup, and queues a reload. See `docs/ZONE_EDITOR.md` for the full guide.

## Privacy zone example

Add this to `config.json` to blur the left side of the image:

```json
"privacy_zones": [
  {
    "name": "bed area",
    "x1": 0.0,
    "y1": 0.0,
    "x2": 0.35,
    "y2": 1.0,
    "mode": "blur"
  }
]
```

Use values from `0.0` to `1.0` for percentages, or pixel coordinates if you prefer.

For a full blackout zone:

```json
"privacy_zones": [
  {
    "name": "monitor",
    "x1": 100,
    "y1": 80,
    "x2": 420,
    "y2": 280,
    "mode": "blackout"
  }
]
```

## Ignore zone example

Ignore zones prevent detections from counting if the centre of the person box lands inside the zone:

```json
"ignore_zones": [
  {
    "name": "window reflection",
    "x1": 0.70,
    "y1": 0.0,
    "x2": 1.0,
    "y2": 0.45
  }
]
```

## Keyboard controls

While the camera window is open:

- `q` quit
- `a` arm/disarm
- `s` save manual snapshot
- `c` open settings
- `v` toggle detection boxes
- `d` open dashboard

## Recommended settings

- `confidence_threshold`: `0.55`
- `person_confirm_seconds`: `0.6`
- `empty_reset_seconds`: `4`
- `detection_fps_limit`: `5`
- `alert_cooldown_seconds`: `60`
- `dashboard_host`: `127.0.0.1`
- `apply_privacy_zones_to_preview`: `true`
- `apply_privacy_zones_to_snapshots`: `true`
- `apply_privacy_zones_to_clips`: `true`

## Open-source status

RoomSentry is MIT licensed. See:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `CODE_OF_CONDUCT.md`
- `docs/ROADMAP.md`
- `docs/ISSUE_SEEDS.md`
- `docs/ZONE_EDITOR.md`
- `docs/TRAY_APP.md`
- `docs/EVENT_REVIEW.md`
