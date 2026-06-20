import argparse
import importlib.util
import json
import platform
import sqlite3
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

REQUIRED_FILES = [
    "room_sentry.py",
    "dashboard_server.py",
    "settings_gui.py",
    "migrate_config.py",
    "validate_config.py",
    "requirements.txt",
    "config.example.json",
]
REQUIRED_MODULES = ["cv2", "requests", "ultralytics"]


def check(name, ok, message=""):
    icon = "OK " if ok else "BAD"
    print(f"[{icon}] {name}{(': ' + message) if message else ''}")
    return ok


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def validate_config(config):
    ok = True
    numeric_ranges = {
        "confidence_threshold": (0.05, 1.0),
        "person_confirm_seconds": (0.0, 30.0),
        "alert_cooldown_seconds": (0, 86400),
        "detection_fps_limit": (0, 60),
        "empty_reset_seconds": (0, 300),
        "dashboard_port": (1, 65535),
    }
    for key, (lo, hi) in numeric_ranges.items():
        try:
            value = float(config.get(key))
            ok &= check(f"config.{key}", lo <= value <= hi, f"{value} expected {lo}-{hi}")
        except Exception as exc:
            ok &= check(f"config.{key}", False, str(exc))
    for zones_key in ["ignore_zones", "privacy_zones"]:
        zones = config.get(zones_key, [])
        if isinstance(zones, list):
            ok &= check(f"config.{zones_key}", True, f"{len(zones)} zone(s)")
        else:
            ok &= check(f"config.{zones_key}", False, "must be a list")
    host = str(config.get("dashboard_host", "127.0.0.1"))
    ok &= check("dashboard host", host in {"127.0.0.1", "localhost"}, f"{host} (localhost is safest)")
    return ok


def main():
    parser = argparse.ArgumentParser(description="RoomSentry diagnostics")
    parser.add_argument("--camera", action="store_true", help="Also try opening the configured camera")
    args = parser.parse_args()

    print("RoomSentry Doctor")
    print(f"Python: {sys.version.split()[0]}")
    print(f"OS: {platform.platform()}")
    all_ok = True

    all_ok &= check("project folder", BASE_DIR.exists(), str(BASE_DIR))
    for file_name in REQUIRED_FILES:
        all_ok &= check(file_name, (BASE_DIR / file_name).exists())

    if not CONFIG_PATH.exists():
        print("config.json missing; run: python migrate_config.py")
        all_ok = False
        config = {}
    else:
        try:
            config = load_config()
            all_ok &= check("config.json", isinstance(config, dict), "valid JSON object")
        except Exception as exc:
            config = {}
            all_ok &= check("config.json", False, str(exc))

    for folder_key, default in [("snapshots_dir", "snapshots"), ("logs_dir", "logs"), ("events_dir", "events"), ("clips_dir", "clips"), ("runtime_dir", "runtime")]:
        folder = BASE_DIR / str(config.get(folder_key, default))
        try:
            folder.mkdir(parents=True, exist_ok=True)
            all_ok &= check(f"folder {folder_key}", folder.exists(), folder.name)
        except Exception as exc:
            all_ok &= check(f"folder {folder_key}", False, str(exc))

    for module in REQUIRED_MODULES:
        all_ok &= check(f"python module {module}", importlib.util.find_spec(module) is not None)

    if config:
        all_ok &= validate_config(config)
        db_path = BASE_DIR / str(config.get("events_db_path", "events/roomsentry_events.sqlite3"))
        try:
            db_path.parent.mkdir(parents=True, exist_ok=True)
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE IF NOT EXISTS doctor_test (id INTEGER)")
                conn.execute("DROP TABLE doctor_test")
            all_ok &= check("SQLite events DB writable", True, str(db_path))
        except Exception as exc:
            all_ok &= check("SQLite events DB writable", False, str(exc))

    if args.camera and config:
        try:
            import cv2
            source = config.get("camera_url") or int(config.get("camera_index", 0))
            cap = cv2.VideoCapture(source)
            opened = cap.isOpened()
            if opened:
                ok, _ = cap.read()
                all_ok &= check("camera open/read", ok, str(source))
            else:
                all_ok &= check("camera open/read", False, str(source))
            cap.release()
        except Exception as exc:
            all_ok &= check("camera open/read", False, str(exc))

    print("\nResult:", "PASS" if all_ok else "CHECK ITEMS ABOVE")
    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
