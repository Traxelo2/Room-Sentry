import ctypes
import json
import platform
import shutil
import sqlite3
import subprocess
import sys
import time
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import cv2
import requests
from ultralytics import YOLO

APP_NAME = "RoomSentry"
APP_VERSION = "1.8.0"
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"

DEFAULT_CONFIG: Dict[str, Any] = {
    "camera_index": 0,
    "camera_url": "",
    "yolo_model": "yolov8n.pt",
    "confidence_threshold": 0.55,
    "person_confirm_seconds": 0.6,
    "alert_cooldown_seconds": 60,
    "save_snapshots": True,
    "snapshots_dir": "snapshots",
    "logs_dir": "logs",
    "events_dir": "events",
    "clips_dir": "clips",
    "runtime_dir": "runtime",
    "events_db_path": "events/roomsentry_events.sqlite3",
    "events_jsonl_path": "events/events.jsonl",
    "discord_webhook_url": "",
    "send_snapshot_to_discord": True,
    "telegram_bot_token": "",
    "telegram_chat_id": "",
    "send_snapshot_to_telegram": True,
    "ntfy_url": "",
    "generic_webhook_url": "",
    "use_ollama": False,
    "ollama_url": "http://127.0.0.1:11434/api/generate",
    "ollama_model": "llama3.1:8b",
    "show_preview_window": True,
    "draw_detection_boxes": True,
    "draw_ignore_zones": True,
    "privacy_zones": [],
    "draw_privacy_zones": True,
    "apply_privacy_zones_to_preview": True,
    "apply_privacy_zones_to_snapshots": True,
    "apply_privacy_zones_to_clips": True,
    "arm_on_start": True,
    "minimum_seconds_between_saved_snapshots": 15,
    "person_label": "person",
    "camera_width": 640,
    "camera_height": 480,
    "detection_fps_limit": 5,
    "empty_reset_seconds": 4,
    "alert_only_when_armed": True,
    "play_sound_on_alert": False,
    "alert_sound_path": "",
    "speak_alert_on_windows": False,
    "voice_alert_text": "RoomSentry alert: someone is in the room.",
    "discord_test_message": "RoomSentry test alert",
    "idle_auto_arm_enabled": False,
    "idle_auto_arm_seconds": 300,
    "timestamp_snapshots": True,
    "blur_saved_snapshots": False,
    "save_clips": False,
    "clip_pre_seconds": 3,
    "clip_post_seconds": 5,
    "clip_fps": 8,
    "auto_delete_enabled": False,
    "auto_delete_days": 7,
    "ignore_zones": [],
    "motion_prefilter_enabled": False,
    "motion_threshold": 9000,
    "open_dashboard_on_start": False,
    "dashboard_host": "127.0.0.1",
    "dashboard_port": 8765,
    "dashboard_command_token": "",
    "status_update_seconds": 1.0,
    "heartbeat_timeout_seconds": 8,
    "camera_reconnect_seconds": 1.0,
    "save_runtime_status": True,
}


def now_stamp() -> str:
    return datetime.now().strftime("%Y-%m-%d_%H-%M-%S")


def app_path(value: str, default: str) -> Path:
    raw = str(value or default).strip()
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


def load_config() -> Dict[str, Any]:
    if not CONFIG_PATH.exists():
        example = BASE_DIR / "config.example.json"
        if example.exists():
            CONFIG_PATH.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
        else:
            CONFIG_PATH.write_text(json.dumps(DEFAULT_CONFIG, indent=4), encoding="utf-8")

    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        user_config = json.load(f)

    config = dict(DEFAULT_CONFIG)
    config.update(user_config)

    # Keep config migrated forward without deleting any unknown future keys.
    if set(DEFAULT_CONFIG.keys()) - set(user_config.keys()):
        merged = dict(user_config)
        for key, value in DEFAULT_CONFIG.items():
            merged.setdefault(key, value)
        CONFIG_PATH.write_text(json.dumps(merged, indent=4), encoding="utf-8")
        config = merged

    return config


def ensure_dirs(config: Dict[str, Any]) -> None:
    for key, default in [
        ("snapshots_dir", "snapshots"),
        ("logs_dir", "logs"),
        ("events_dir", "events"),
        ("clips_dir", "clips"),
        ("runtime_dir", "runtime"),
    ]:
        app_path(config.get(key, default), default).mkdir(parents=True, exist_ok=True)


def log_event(config: Dict[str, Any], message: str) -> None:
    logs_dir = app_path(config.get("logs_dir", "logs"), "logs")
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = logs_dir / f"room_sentry_{datetime.now().strftime('%Y-%m-%d')}.log"
    line = f"[{datetime.now().isoformat(timespec='seconds')}] {message}\n"
    with log_file.open("a", encoding="utf-8") as f:
        f.write(line)
    print(line.strip(), flush=True)


def init_event_db(config: Dict[str, Any]) -> None:
    db_path = app_path(config.get("events_db_path", "events/roomsentry_events.sqlite3"), "events/roomsentry_events.sqlite3")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                event_type TEXT NOT NULL,
                message TEXT NOT NULL,
                confidence REAL,
                person_count INTEGER,
                snapshot_path TEXT,
                clip_path TEXT,
                payload_json TEXT
            )
            """
        )
        existing = {row[1] for row in conn.execute("PRAGMA table_info(events)").fetchall()}
        for name, ddl in {
            "important": "INTEGER DEFAULT 0",
            "false_positive": "INTEGER DEFAULT 0",
            "review_note": "TEXT DEFAULT ''",
            "reviewed_at": "TEXT",
        }.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
        conn.commit()


def record_event(
    config: Dict[str, Any],
    event_type: str,
    message: str,
    confidence: Optional[float] = None,
    person_count: Optional[int] = None,
    snapshot_path: Optional[Path] = None,
    clip_path: Optional[Path] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> None:
    created_at = datetime.now().isoformat(timespec="seconds")
    payload = payload or {}

    def rel(path: Optional[Path]) -> Optional[str]:
        if not path:
            return None
        try:
            return str(path.relative_to(BASE_DIR))
        except Exception:
            return str(path)

    db_path = app_path(config.get("events_db_path", "events/roomsentry_events.sqlite3"), "events/roomsentry_events.sqlite3")
    try:
        with sqlite3.connect(db_path) as conn:
            conn.execute(
                """
                INSERT INTO events
                (created_at, event_type, message, confidence, person_count, snapshot_path, clip_path, payload_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    created_at,
                    event_type,
                    message,
                    confidence,
                    person_count,
                    rel(snapshot_path),
                    rel(clip_path),
                    json.dumps(payload, ensure_ascii=False),
                ),
            )
            conn.commit()
    except Exception as exc:
        log_event(config, f"Event DB write failed: {exc}")

    jsonl_path = app_path(config.get("events_jsonl_path", "events/events.jsonl"), "events/events.jsonl")
    try:
        jsonl_path.parent.mkdir(parents=True, exist_ok=True)
        row = {
            "created_at": created_at,
            "event_type": event_type,
            "message": message,
            "confidence": confidence,
            "person_count": person_count,
            "snapshot_path": rel(snapshot_path),
            "clip_path": rel(clip_path),
            "payload": payload,
        }
        with jsonl_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:
        log_event(config, f"Event JSONL write failed: {exc}")


def runtime_file(config: Dict[str, Any], name: str) -> Path:
    runtime_dir = app_path(config.get("runtime_dir", "runtime"), "runtime")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / name


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def write_runtime_state(config: Dict[str, Any], payload: Dict[str, Any]) -> None:
    if not config.get("save_runtime_status", True):
        return
    try:
        payload = dict(payload)
        payload.setdefault("app_name", APP_NAME)
        payload.setdefault("app_version", APP_VERSION)
        payload.setdefault("updated_at", datetime.now().isoformat(timespec="seconds"))
        payload.setdefault("updated_at_epoch", time.time())
        atomic_write_json(runtime_file(config, "state.json"), payload)
    except Exception:
        pass


def pop_control_command(config: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    path = runtime_file(config, "command.json")
    if not path.exists():
        return None
    try:
        raw = path.read_text(encoding="utf-8")
        path.unlink(missing_ok=True)
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception as exc:
        try:
            path.unlink(missing_ok=True)
        except Exception:
            pass
        log_event(config, f"Bad dashboard command ignored: {exc}")
    return None


def write_control_ack(config: Dict[str, Any], command: str, ok: bool, message: str) -> None:
    try:
        atomic_write_json(
            runtime_file(config, "last_command_ack.json"),
            {
                "command": command,
                "ok": ok,
                "message": message,
                "created_at": datetime.now().isoformat(timespec="seconds"),
                "created_at_epoch": time.time(),
            },
        )
    except Exception:
        pass


def build_ollama_alert(config: Dict[str, Any], event_text: str) -> str:
    if not config.get("use_ollama", False):
        return event_text

    prompt = f"""
You are a local room security assistant.
Write a short, calm alert message for the owner.

Rules:
- Do not exaggerate.
- Mention that a person was detected.
- Keep it under 25 words.
- No police/emergency wording unless explicitly stated.
- No extra explanation.

Event:
{event_text}
""".strip()

    try:
        response = requests.post(
            config.get("ollama_url", ""),
            json={"model": config.get("ollama_model", ""), "prompt": prompt, "stream": False},
            timeout=12,
        )
        response.raise_for_status()
        data = response.json()
        text = data.get("response", "").strip()
        return text or event_text
    except Exception as e:
        return f"{event_text} (Ollama unavailable: {e})"


def send_discord_alert(config: Dict[str, Any], message: str, snapshot_path: Optional[Path]) -> None:
    webhook = str(config.get("discord_webhook_url", "")).strip()
    if not webhook:
        return
    try:
        if snapshot_path and snapshot_path.exists() and config.get("send_snapshot_to_discord", True):
            with snapshot_path.open("rb") as image_file:
                requests.post(webhook, data={"content": message}, files={"file": image_file}, timeout=15).raise_for_status()
        else:
            requests.post(webhook, json={"content": message}, timeout=15).raise_for_status()
    except Exception as e:
        log_event(config, f"Discord alert failed: {e}")


def send_telegram_alert(config: Dict[str, Any], message: str, snapshot_path: Optional[Path]) -> None:
    token = str(config.get("telegram_bot_token", "")).strip()
    chat_id = str(config.get("telegram_chat_id", "")).strip()
    if not token or not chat_id:
        return
    try:
        base = f"https://api.telegram.org/bot{token}"
        if snapshot_path and snapshot_path.exists() and config.get("send_snapshot_to_telegram", True):
            with snapshot_path.open("rb") as image_file:
                requests.post(
                    f"{base}/sendPhoto",
                    data={"chat_id": chat_id, "caption": message},
                    files={"photo": image_file},
                    timeout=20,
                ).raise_for_status()
        else:
            requests.post(f"{base}/sendMessage", json={"chat_id": chat_id, "text": message}, timeout=15).raise_for_status()
    except Exception as e:
        log_event(config, f"Telegram alert failed: {e}")


def send_ntfy_alert(config: Dict[str, Any], message: str) -> None:
    url = str(config.get("ntfy_url", "")).strip()
    if not url:
        return
    try:
        requests.post(url, data=message.encode("utf-8"), headers={"Title": "RoomSentry", "Priority": "high"}, timeout=15).raise_for_status()
    except Exception as e:
        log_event(config, f"ntfy alert failed: {e}")


def send_generic_webhook(config: Dict[str, Any], payload: Dict[str, Any]) -> None:
    url = str(config.get("generic_webhook_url", "")).strip()
    if not url:
        return
    try:
        requests.post(url, json=payload, timeout=15).raise_for_status()
    except Exception as e:
        log_event(config, f"Generic webhook failed: {e}")


def open_camera(config: Dict[str, Any]):
    camera_url = str(config.get("camera_url", "")).strip()
    if camera_url:
        cap = cv2.VideoCapture(camera_url)
    else:
        cap = cv2.VideoCapture(int(config.get("camera_index", 0)))
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, int(config.get("camera_width", 640)))
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, int(config.get("camera_height", 480)))
    return cap


def timestamp_frame(frame) -> None:
    text = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cv2.putText(frame, text, (10, frame.shape[0] - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)


def blur_boxes(frame, boxes: List[Tuple[int, int, int, int]]) -> None:
    for x1, y1, x2, y2 in boxes:
        x1, y1 = max(0, x1), max(0, y1)
        x2, y2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
        if x2 <= x1 or y2 <= y1:
            continue
        roi = frame[y1:y2, x1:x2]
        blurred = cv2.GaussianBlur(roi, (45, 45), 0)
        frame[y1:y2, x1:x2] = blurred



def _zone_to_pixels(zone: Dict[str, Any], width: int, height: int) -> Optional[Tuple[int, int, int, int]]:
    try:
        x1 = float(zone.get("x1", 0))
        y1 = float(zone.get("y1", 0))
        x2 = float(zone.get("x2", 0))
        y2 = float(zone.get("y2", 0))
        if max(x1, x2, y1, y2) <= 1.0:
            x1, x2 = x1 * width, x2 * width
            y1, y2 = y1 * height, y2 * height
        left = max(0, min(width, int(min(x1, x2))))
        right = max(0, min(width, int(max(x1, x2))))
        top = max(0, min(height, int(min(y1, y2))))
        bottom = max(0, min(height, int(max(y1, y2))))
        if right <= left or bottom <= top:
            return None
        return left, top, right, bottom
    except Exception:
        return None


def apply_privacy_zones(config: Dict[str, Any], frame) -> None:
    zones = config.get("privacy_zones", [])
    if not isinstance(zones, list) or not zones:
        return
    h, w = frame.shape[:2]
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        pixels = _zone_to_pixels(zone, w, h)
        if not pixels:
            continue
        x1, y1, x2, y2 = pixels
        mode = str(zone.get("mode", "blur")).lower()
        roi = frame[y1:y2, x1:x2]
        if mode in {"black", "blackout"}:
            frame[y1:y2, x1:x2] = 0
        else:
            k = int(zone.get("blur_kernel", 51) or 51)
            k = max(3, k if k % 2 == 1 else k + 1)
            frame[y1:y2, x1:x2] = cv2.GaussianBlur(roi, (k, k), 0)


def save_snapshot(config: Dict[str, Any], frame, prefix: str = "person_detected", boxes: Optional[List[Tuple[int, int, int, int]]] = None) -> Path:
    snapshots_dir = app_path(config.get("snapshots_dir", "snapshots"), "snapshots")
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    out = frame.copy()
    if config.get("blur_saved_snapshots", False) and boxes:
        blur_boxes(out, boxes)
    if config.get("apply_privacy_zones_to_snapshots", True):
        apply_privacy_zones(config, out)
    if config.get("timestamp_snapshots", True):
        timestamp_frame(out)
    path = snapshots_dir / f"{prefix}_{now_stamp()}.jpg"
    cv2.imwrite(str(path), out)
    return path


def save_event_clip(config: Dict[str, Any], pre_frames, cap, current_frame) -> Optional[Path]:
    if not config.get("save_clips", False):
        return None
    try:
        clips_dir = app_path(config.get("clips_dir", "clips"), "clips")
        clips_dir.mkdir(parents=True, exist_ok=True)
        path = clips_dir / f"event_clip_{now_stamp()}.mp4"
        fps = max(1, int(config.get("clip_fps", 8)))
        frames = [f.copy() for f in pre_frames]
        frames.append(current_frame.copy())
        if config.get("apply_privacy_zones_to_clips", True):
            for item in frames:
                apply_privacy_zones(config, item)
        post_count = max(0, int(float(config.get("clip_post_seconds", 5)) * fps))
        for _ in range(post_count):
            ok, frame = cap.read()
            if ok:
                if config.get("apply_privacy_zones_to_clips", True):
                    apply_privacy_zones(config, frame)
                if config.get("timestamp_snapshots", True):
                    timestamp_frame(frame)
                frames.append(frame.copy())
            time.sleep(1.0 / fps)
        if not frames:
            return None
        height, width = frames[0].shape[:2]
        writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
        for frame in frames:
            if frame.shape[1] != width or frame.shape[0] != height:
                frame = cv2.resize(frame, (width, height))
            writer.write(frame)
        writer.release()
        return path
    except Exception as exc:
        log_event(config, f"Clip save failed: {exc}")
        return None


def play_alert_sound(config: Dict[str, Any]) -> None:
    if not config.get("play_sound_on_alert", False):
        return
    try:
        import winsound
        sound_path = str(config.get("alert_sound_path", "")).strip()
        if sound_path and app_path(sound_path, sound_path).exists():
            winsound.PlaySound(str(app_path(sound_path, sound_path)), winsound.SND_FILENAME | winsound.SND_ASYNC)
        else:
            winsound.MessageBeep()
    except Exception:
        return


def speak_alert(config: Dict[str, Any]) -> None:
    if not config.get("speak_alert_on_windows", False):
        return
    if platform.system().lower() != "windows":
        return
    text = str(config.get("voice_alert_text", "RoomSentry alert: someone is in the room.")).replace("'", "")
    try:
        subprocess.Popen(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Add-Type -AssemblyName System.Speech; "
                f"$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak('{text}')",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return


def get_idle_duration() -> float:
    if platform.system().lower() != "windows":
        return 0.0
    try:
        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_ulong)]
        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            millis = ctypes.windll.kernel32.GetTickCount() - lii.dwTime
            return millis / 1000.0
    except Exception:
        return 0.0
    return 0.0


def in_ignore_zone(config: Dict[str, Any], x: float, y: float, width: int, height: int) -> bool:
    zones = config.get("ignore_zones", [])
    if not isinstance(zones, list):
        return False
    for zone in zones:
        if not isinstance(zone, dict):
            continue
        try:
            x1 = float(zone.get("x1", 0))
            y1 = float(zone.get("y1", 0))
            x2 = float(zone.get("x2", 0))
            y2 = float(zone.get("y2", 0))
            if max(x1, x2, y1, y2) <= 1.0:
                x1, x2 = x1 * width, x2 * width
                y1, y2 = y1 * height, y2 * height
            if min(x1, x2) <= x <= max(x1, x2) and min(y1, y2) <= y <= max(y1, y2):
                return True
        except Exception:
            continue
    return False


def draw_zones(config: Dict[str, Any], frame) -> None:
    if not config.get("draw_ignore_zones", True):
        return
    zones = config.get("ignore_zones", [])
    if not isinstance(zones, list):
        return
    h, w = frame.shape[:2]
    for i, zone in enumerate(zones):
        if not isinstance(zone, dict):
            continue
        try:
            x1 = float(zone.get("x1", 0))
            y1 = float(zone.get("y1", 0))
            x2 = float(zone.get("x2", 0))
            y2 = float(zone.get("y2", 0))
            if max(x1, x2, y1, y2) <= 1.0:
                x1, x2 = x1 * w, x2 * w
                y1, y2 = y1 * h, y2 * h
            p1 = (int(min(x1, x2)), int(min(y1, y2)))
            p2 = (int(max(x1, x2)), int(max(y1, y2)))
            cv2.rectangle(frame, p1, p2, (80, 80, 80), 2)
            label = str(zone.get("name", f"ignore {i+1}"))
            cv2.putText(frame, label, (p1[0] + 5, max(p1[1] + 20, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (180, 180, 180), 1)
        except Exception:
            continue



def draw_privacy_zones(config: Dict[str, Any], frame) -> None:
    if not config.get("draw_privacy_zones", True):
        return
    zones = config.get("privacy_zones", [])
    if not isinstance(zones, list):
        return
    h, w = frame.shape[:2]
    for i, zone in enumerate(zones):
        if not isinstance(zone, dict):
            continue
        pixels = _zone_to_pixels(zone, w, h)
        if not pixels:
            continue
        x1, y1, x2, y2 = pixels
        cv2.rectangle(frame, (x1, y1), (x2, y2), (150, 80, 150), 2)
        label = str(zone.get("name", f"privacy {i+1}"))
        cv2.putText(frame, label, (x1 + 5, max(y1 + 20, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (220, 170, 220), 1)


def run_settings_gui(config: Dict[str, Any]) -> Dict[str, Any]:
    log_event(config, "Settings GUI opened. Camera feed paused.")
    subprocess.run([sys.executable, str(BASE_DIR / "settings_gui.py")], cwd=str(BASE_DIR), check=False)
    new_config = load_config()
    ensure_dirs(new_config)
    log_event(new_config, "Settings reloaded from GUI.")
    return new_config


def maybe_auto_delete(config: Dict[str, Any]) -> None:
    if not config.get("auto_delete_enabled", False):
        return
    days = float(config.get("auto_delete_days", 7))
    cutoff = time.time() - days * 86400
    for key, default, patterns in [
        ("snapshots_dir", "snapshots", ["*.jpg", "*.jpeg", "*.png"]),
        ("clips_dir", "clips", ["*.mp4", "*.avi"]),
        ("logs_dir", "logs", ["*.log"]),
    ]:
        folder = app_path(config.get(key, default), default)
        if not folder.exists():
            continue
        for pattern in patterns:
            for path in folder.glob(pattern):
                try:
                    if path.stat().st_mtime < cutoff:
                        path.unlink()
                except Exception:
                    pass


def launch_dashboard() -> None:
    dashboard = BASE_DIR / "dashboard_server.py"
    if dashboard.exists():
        subprocess.Popen([sys.executable, str(dashboard), "--open"], cwd=str(BASE_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def motion_detected(config: Dict[str, Any], prev_gray, frame) -> Tuple[bool, Any]:
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (21, 21), 0)
    if prev_gray is None:
        return True, gray
    delta = cv2.absdiff(prev_gray, gray)
    _, thresh = cv2.threshold(delta, 25, 255, cv2.THRESH_BINARY)
    score = int(thresh.sum() / 255)
    return score >= int(config.get("motion_threshold", 9000)), gray


def copy_latest_frame(config: Dict[str, Any], frame) -> None:
    try:
        path = runtime_file(config, "latest_frame.jpg")
        out = frame.copy()
        if config.get("apply_privacy_zones_to_preview", True):
            apply_privacy_zones(config, out)
        if config.get("timestamp_snapshots", True):
            timestamp_frame(out)
        cv2.imwrite(str(path), out)
    except Exception:
        pass


def handle_control_command(
    config: Dict[str, Any],
    command: Dict[str, Any],
    armed: bool,
    frame,
    person_boxes: Optional[List[Tuple[int, int, int, int]]] = None,
) -> Tuple[Dict[str, Any], bool, bool]:
    name = str(command.get("command", "")).strip().lower()
    should_quit = False
    person_boxes = person_boxes or []
    try:
        if name == "arm":
            armed = True
            message = "Dashboard command: armed."
            log_event(config, message)
            record_event(config, "dashboard_arm", message, payload={"armed": armed})
            write_control_ack(config, name, True, message)
        elif name == "disarm":
            armed = False
            message = "Dashboard command: disarmed."
            log_event(config, message)
            record_event(config, "dashboard_disarm", message, payload={"armed": armed})
            write_control_ack(config, name, True, message)
        elif name == "toggle_arm":
            armed = not armed
            message = f"Dashboard command: {'armed' if armed else 'disarmed'}."
            log_event(config, message)
            record_event(config, "dashboard_toggle_arm", message, payload={"armed": armed})
            write_control_ack(config, name, True, message)
        elif name == "snapshot":
            if frame is None:
                message = "No camera frame available yet."
                write_control_ack(config, name, False, message)
            else:
                path = save_snapshot(config, frame, prefix="dashboard_snapshot", boxes=person_boxes)
                message = f"Dashboard snapshot saved: {path}"
                log_event(config, message)
                record_event(config, "dashboard_snapshot", message, snapshot_path=path)
                write_control_ack(config, name, True, message)
        elif name == "reload_config":
            new_config = load_config()
            ensure_dirs(new_config)
            message = "Dashboard command: config reloaded."
            log_event(new_config, message)
            record_event(new_config, "dashboard_reload_config", message)
            write_control_ack(new_config, name, True, message)
            config = new_config
        elif name == "cleanup_old_files":
            maybe_auto_delete(config)
            message = "Dashboard command: cleanup completed."
            log_event(config, message)
            record_event(config, "dashboard_cleanup", message)
            write_control_ack(config, name, True, message)
        elif name == "quit":
            should_quit = True
            message = "Dashboard command: quit requested."
            log_event(config, message)
            record_event(config, "dashboard_quit", message)
            write_control_ack(config, name, True, message)
        else:
            message = f"Unknown command: {name}"
            write_control_ack(config, name or "unknown", False, message)
    except Exception as exc:
        write_control_ack(config, name or "unknown", False, f"Command failed: {exc}")
    return config, armed, should_quit


def main() -> None:
    config = load_config()
    ensure_dirs(config)
    init_event_db(config)
    maybe_auto_delete(config)

    armed = bool(config.get("arm_on_start", True))
    draw_boxes = bool(config.get("draw_detection_boxes", True))

    print(f"{APP_NAME} starting...")
    print("Press q quit | a arm/disarm | s snapshot | c settings | v boxes | d dashboard")
    log_event(config, f"RoomSentry started. Initial status: {'ARMED' if armed else 'DISARMED'}")
    record_event(config, "system_started", f"RoomSentry started. Initial status: {'ARMED' if armed else 'DISARMED'}")
    write_runtime_state(config, {"running": True, "armed": armed, "room_state": "STARTING", "camera_ok": False, "message": "Starting"})

    if config.get("open_dashboard_on_start", False):
        launch_dashboard()

    model = YOLO(config.get("yolo_model", "yolov8n.pt"))
    cap = open_camera(config)
    if not cap.isOpened():
        write_runtime_state(config, {"running": False, "armed": armed, "room_state": "ERROR", "camera_ok": False, "message": "Could not open camera"})
        raise RuntimeError("Could not open camera. Try changing camera_index or camera_url in config.json.")

    fps = max(1, int(config.get("clip_fps", 8)))
    pre_frames = deque(maxlen=max(1, int(float(config.get("clip_pre_seconds", 3)) * fps)))
    last_alert_time = 0.0
    last_snapshot_time = 0.0
    state = "EMPTY"
    candidate_person_since = 0.0
    last_person_time = 0.0
    last_frame_time = 0.0
    last_status_write = 0.0
    status_frames = 0
    status_window_start = time.time()
    detector_fps = 0.0
    prev_gray = None
    latest_message = "Started"
    last_snapshot_preview = 0.0

    while True:
        current_time = time.time()
        fps_limit = float(config.get("detection_fps_limit", 5))
        if fps_limit > 0 and current_time - last_frame_time < (1.0 / fps_limit):
            time.sleep(0.01)
            continue
        last_frame_time = current_time

        ok, frame = cap.read()
        if not ok:
            latest_message = "Camera frame read failed. Reconnecting..."
            log_event(config, latest_message)
            write_runtime_state(config, {"running": True, "armed": armed, "room_state": state, "camera_ok": False, "message": latest_message})
            cap.release()
            time.sleep(float(config.get("camera_reconnect_seconds", 1.0)))
            cap = open_camera(config)
            continue

        command = pop_control_command(config)
        if command:
            config, armed, should_quit = handle_control_command(config, command, armed, frame)
            if should_quit:
                break

        pre_frame = frame.copy()
        if config.get("timestamp_snapshots", True):
            timestamp_frame(pre_frame)
        pre_frames.append(pre_frame)

        if current_time - last_snapshot_preview >= 2.0:
            copy_latest_frame(config, frame)
            last_snapshot_preview = current_time

        if config.get("idle_auto_arm_enabled", False):
            idle_seconds = get_idle_duration()
            threshold = float(config.get("idle_auto_arm_seconds", 300))
            if idle_seconds > threshold and not armed:
                armed = True
                latest_message = f"System auto-armed due to user idle ({threshold:.0f}s)."
                log_event(config, latest_message)
                record_event(config, "auto_armed", latest_message)

        if config.get("motion_prefilter_enabled", False):
            moved, prev_gray = motion_detected(config, prev_gray, frame)
            if not moved and state == "EMPTY":
                results = []
            else:
                results = model(frame, verbose=False)
        else:
            results = model(frame, verbose=False)

        status_frames += 1
        elapsed = current_time - status_window_start
        if elapsed >= 2.0:
            detector_fps = status_frames / elapsed
            status_frames = 0
            status_window_start = current_time

        person_found = False
        best_confidence = 0.0
        person_count = 0
        person_boxes: List[Tuple[int, int, int, int]] = []
        confidence_threshold = float(config.get("confidence_threshold", 0.55))
        person_label = config.get("person_label", "person")
        h, w = frame.shape[:2]

        for result in results:
            for box in result.boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])
                label = model.names[class_id]
                if label != person_label or confidence < confidence_threshold:
                    continue
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                if in_ignore_zone(config, center_x, center_y, w, h):
                    if draw_boxes:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 1)
                        cv2.putText(frame, "IGNORED", (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 80), 2)
                    continue
                person_found = True
                person_count += 1
                best_confidence = max(best_confidence, confidence)
                person_boxes.append((x1, y1, x2, y2))
                if draw_boxes:
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
                    cv2.putText(frame, f"PERSON {confidence:.2f}", (x1, max(y1 - 10, 20)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

        draw_zones(config, frame)
        draw_privacy_zones(config, frame)

        # Handle a command that benefits from boxes after detection.
        command = pop_control_command(config)
        if command:
            config, armed, should_quit = handle_control_command(config, command, armed, frame, person_boxes)
            if should_quit:
                break

        if person_found:
            last_person_time = current_time
            if candidate_person_since == 0.0:
                candidate_person_since = current_time
        else:
            candidate_person_since = 0.0

        confirm_seconds = float(config.get("person_confirm_seconds", 0.6))
        person_confirmed = person_found and (current_time - candidate_person_since >= confirm_seconds)

        status_text = "ARMED" if armed else "DISARMED"
        cv2.putText(frame, f"{APP_NAME} | {status_text} | {state}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)

        if person_confirmed and state == "EMPTY":
            state = "PERSON_PRESENT"
            raw_event = f"Person detected in room. Count: {person_count}. Best confidence: {best_confidence:.2f}."
            latest_message = raw_event
            log_event(config, f"State change: EMPTY -> PERSON_PRESENT (Count: {person_count}, Conf: {best_confidence:.2f})")

            alert_only_when_armed = bool(config.get("alert_only_when_armed", True))
            snapshot_path = None
            clip_path = None

            if armed or not alert_only_when_armed:
                alert_cooldown = float(config.get("alert_cooldown_seconds", 60))
                if current_time - last_alert_time >= alert_cooldown:
                    play_alert_sound(config)
                    speak_alert(config)
                    if config.get("save_snapshots", True):
                        min_snapshot_gap = float(config.get("minimum_seconds_between_saved_snapshots", 15))
                        if current_time - last_snapshot_time >= min_snapshot_gap:
                            snapshot_path = save_snapshot(config, frame, boxes=person_boxes)
                            last_snapshot_time = current_time
                    clip_path = save_event_clip(config, pre_frames, cap, frame)
                    alert_message = "🚨 " + build_ollama_alert(config, raw_event)
                    log_event(config, raw_event)
                    payload = {
                        "event": "person_detected",
                        "message": raw_event,
                        "confidence": best_confidence,
                        "person_count": person_count,
                        "snapshot_path": str(snapshot_path.relative_to(BASE_DIR)) if snapshot_path else None,
                        "clip_path": str(clip_path.relative_to(BASE_DIR)) if clip_path else None,
                        "armed": armed,
                    }
                    send_discord_alert(config, alert_message, snapshot_path)
                    send_telegram_alert(config, alert_message, snapshot_path)
                    send_ntfy_alert(config, alert_message)
                    send_generic_webhook(config, payload)
                    record_event(config, "person_detected", raw_event, best_confidence, person_count, snapshot_path, clip_path, payload)
                    last_alert_time = current_time
                else:
                    record_event(config, "person_detected_cooldown", raw_event, best_confidence, person_count, payload={"armed": armed})
            else:
                record_event(config, "person_detected_disarmed", raw_event, best_confidence, person_count, payload={"armed": armed})

        if not person_found and state == "PERSON_PRESENT":
            empty_reset_seconds = float(config.get("empty_reset_seconds", 4.0))
            if current_time - last_person_time >= empty_reset_seconds:
                state = "EMPTY"
                latest_message = "State change: PERSON_PRESENT -> EMPTY (Room is clear)"
                log_event(config, latest_message)
                record_event(config, "room_clear", latest_message)

        if current_time - last_status_write >= float(config.get("status_update_seconds", 1.0)):
            write_runtime_state(
                config,
                {
                    "running": True,
                    "armed": armed,
                    "room_state": state,
                    "camera_ok": True,
                    "person_visible": person_found,
                    "person_count": person_count,
                    "best_confidence": round(best_confidence, 4),
                    "detector_fps": round(detector_fps, 2),
                    "preview_path": "runtime/latest_frame.jpg",
                    "message": latest_message,
                    "last_person_seen_epoch": last_person_time or None,
                },
            )
            last_status_write = current_time

        if config.get("show_preview_window", True):
            cv2.imshow(APP_NAME, frame)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q"):
                break
            if key == ord("a"):
                armed = not armed
                latest_message = f"Alerts {'armed' if armed else 'disarmed'} by keyboard toggle."
                log_event(config, latest_message)
                record_event(config, "manual_arm_toggle", latest_message, payload={"armed": armed})
            if key == ord("s"):
                path = save_snapshot(config, frame, prefix="manual_snapshot")
                latest_message = f"Manual snapshot saved: {path}"
                log_event(config, latest_message)
                record_event(config, "manual_snapshot", latest_message, snapshot_path=path)
            if key == ord("v"):
                draw_boxes = not draw_boxes
                latest_message = f"Detection boxes {'enabled' if draw_boxes else 'disabled'}."
                log_event(config, latest_message)
            if key == ord("c"):
                config = run_settings_gui(config)
            if key == ord("d"):
                launch_dashboard()
        else:
            time.sleep(0.02)

    cap.release()
    cv2.destroyAllWindows()
    latest_message = "RoomSentry stopped."
    log_event(config, latest_message)
    record_event(config, "system_stopped", latest_message)
    write_runtime_state(config, {"running": False, "armed": armed, "room_state": state, "camera_ok": False, "message": latest_message})


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        cfg = load_config()
        write_runtime_state(cfg, {"running": False, "armed": False, "room_state": "STOPPED", "camera_ok": False, "message": "Stopped by keyboard interrupt"})
        raise
