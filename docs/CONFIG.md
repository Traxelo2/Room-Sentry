# Configuration Reference

RoomSentry reads `config.json`. Start by copying `config.example.json`.

## Camera

- `camera_index`: webcam index, usually `0`
- `camera_url`: optional IP camera/stream URL. If set, this is used instead of `camera_index`
- `camera_width`: requested camera width
- `camera_height`: requested camera height

## Detection

- `yolo_model`: YOLO model path/name, default `yolov8n.pt`
- `confidence_threshold`: minimum person confidence
- `person_confirm_seconds`: how long a person must be seen before alerting
- `detection_fps_limit`: max detection rate
- `motion_prefilter_enabled`: use motion before running person detection
- `motion_threshold`: motion sensitivity threshold

## Alerts

- `alert_only_when_armed`: only alert while armed
- `alert_cooldown_seconds`: minimum seconds between alerts
- `discord_webhook_url`: Discord webhook
- `telegram_bot_token`: Telegram bot token
- `telegram_chat_id`: Telegram chat ID
- `ntfy_url`: ntfy topic URL
- `generic_webhook_url`: generic webhook endpoint

## Storage

- `save_snapshots`: save snapshots for events
- `save_clips`: save MP4 clips for events
- `snapshots_dir`: snapshot folder
- `clips_dir`: clip folder
- `events_db_path`: SQLite database path
- `events_jsonl_path`: JSONL event log path
- `auto_delete_enabled`: delete old runtime files
- `auto_delete_days`: retention days

## Dashboard

- `dashboard_host`: default `127.0.0.1`
- `dashboard_port`: default `8765`
- `dashboard_command_token`: optional token for command calls

Keep `dashboard_host` as `127.0.0.1` unless you are behind a trusted VPN/private tunnel.
