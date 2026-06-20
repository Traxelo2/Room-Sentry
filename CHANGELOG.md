# Changelog

## v1.8.0

- Added dashboard Event Review/Search panel.
- Added event search/filter by text, type, date, important, false positive, snapshot, and clip.
- Added local event review metadata: `important`, `false_positive`, `review_note`, and `reviewed_at`.
- Added dashboard buttons to mark important events and false positives.
- Added review notes from the dashboard.
- Added selected event deletion, with optional local media deletion.
- Added visible JSON export from the dashboard.
- Added daily event summary endpoint and dashboard summary button.
- Added `docs/EVENT_REVIEW.md`.
- Version bumped to `1.8.0`.

## v1.7.0

### Added

- Optional Windows tray controller in `tray_app.py`.
- `START_ROOM_SENTRY_TRAY.bat` tray launcher.
- Tray menu actions for open dashboard, arm, disarm, snapshot, reload config, start services, and quit.
- Windows startup shortcut helpers for tray mode.
- `docs/TRAY_APP.md`.
- `pystray` and `pillow` optional desktop dependencies.

### Changed

- Version bumped to `1.7.0`.
- README updated with tray workflow.


## v1.6.0

### Added

- Visual Zone Editor in the local dashboard.
- Canvas overlay for drawing ignore zones and privacy zones on the latest camera preview.
- Dashboard `/api/zones` GET/POST endpoint.
- Config backup creation before dashboard zone saves.
- Automatic config reload command after saving zones.
- `docs/ZONE_EDITOR.md` guide.

### Changed

- Version bumped to `1.6.0`.
- README updated for visual zone editing.
- Privacy blackout mode now accepts both `black` and `blackout`.

## v1.5.0

### Added

- Privacy zones for blurring or blacking out sensitive areas.
- Privacy-zone application for dashboard previews, saved snapshots, and saved clips.
- `validate_config.py` config validator.
- `VALIDATE_CONFIG.bat` and `validate_config_windows.ps1` Windows helpers.
- Dashboard `/api/diagnostics` endpoint with redacted config and runtime health.
- Dashboard diagnostics panel.
- Improved doctor checks for privacy zones and ignore zones.

### Changed

- Version bumped to `1.5.0`.
- README rewritten around the open-source v1.5 workflow.
- `config.example.json` now includes privacy-zone defaults.

### Privacy

- Privacy zones are enabled for previews, snapshots, and clips by default.
- Dashboard diagnostics redacts token/webhook/key-like values.

## v1.4.0

- Local control dashboard.
- Dashboard arm/disarm, snapshot, reload config, cleanup, and quit commands.
- Runtime heartbeat/state file.
- Latest camera preview in dashboard.
- Event timeline and snapshot gallery.
- CSV/JSON event exports.

## v1.3.0

- Event database.
- Alert integrations.
- Snapshot gallery.
- Optional clip recording.
- Ignore zones.
- Auto-delete old files.

## v1.2.0

- Clean portable package.
- Anti-flicker confirmation.
- Better launch scripts.
