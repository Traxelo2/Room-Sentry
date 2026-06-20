# Architecture

RoomSentry is intentionally simple: one local detector process, one local dashboard server, and local files for state/history.

## Components

```text
Camera / IP stream
      ↓
room_sentry.py
  - OpenCV capture
  - optional motion pre-filter
  - YOLO person detection
  - armed/disarmed state
  - snapshots/clips/events
  - alert integrations
      ↓ writes
runtime/state.json
runtime/commands.json
runtime/latest.jpg
events/events.sqlite3
events/events.jsonl
      ↑ reads/writes
 dashboard_server.py
  - localhost browser UI
  - /api/state
  - /api/events
  - /api/command
```

## Data flow

1. `room_sentry.py` opens the configured camera.
2. Frames are checked for motion/person detection.
3. A person must remain visible for `person_confirm_seconds` before an alert event fires.
4. RoomSentry writes a local event row, optional snapshot, optional clip, and runtime status.
5. Enabled alert integrations receive only the configured payload/snapshot.
6. `dashboard_server.py` shows local state and can write simple commands to `runtime/commands.json`.

## Privacy boundaries

- Camera frames are local by default.
- External alert integrations are opt-in.
- The dashboard binds to `127.0.0.1` by default.
- Runtime files, clips, snapshots, logs, and real config files are excluded from Git.

## Extension points

Good future plugin boundaries:

- `detectors/` for YOLO, motion-only, and future model backends.
- `alerts/` for Discord, Telegram, ntfy, webhook, TTS, etc.
- `storage/` for SQLite/JSONL/history exporters.
- `dashboard/` for richer static assets or a future desktop UI.
