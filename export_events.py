import argparse
import csv
import json
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
    return {}


def app_path(value, default):
    path = Path(str(value or default))
    return path if path.is_absolute() else BASE_DIR / path


def fetch_events(config, limit=10000):
    db_path = app_path(config.get("events_db_path", "events/roomsentry_events.sqlite3"), "events/roomsentry_events.sqlite3")
    if not db_path.exists():
        return []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return [dict(row) for row in conn.execute("SELECT * FROM events ORDER BY id DESC LIMIT ?", (limit,))]


def export_csv(events, path):
    fields = ["id", "created_at", "event_type", "message", "confidence", "person_count", "snapshot_path", "clip_path", "payload_json"]
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(events)


def export_json(events, path):
    path.write_text(json.dumps(events, indent=2, ensure_ascii=False), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="Export RoomSentry events")
    parser.add_argument("--format", choices=["csv", "json"], default="csv")
    parser.add_argument("--limit", type=int, default=10000)
    args = parser.parse_args()
    config = load_config()
    events = fetch_events(config, args.limit)
    out_dir = app_path(config.get("events_dir", "events"), "events") / "exports"
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    out = out_dir / f"roomsentry_events_{stamp}.{args.format}"
    if args.format == "csv":
        export_csv(events, out)
    else:
        export_json(events, out)
    print(f"Exported {len(events)} event(s) to {out}")


if __name__ == "__main__":
    main()
