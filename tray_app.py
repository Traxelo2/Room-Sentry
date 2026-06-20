"""Windows tray controller for RoomSentry.

This is intentionally small and optional. It launches RoomSentry and the local
web dashboard, then gives you a system tray menu for common commands.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
import webbrowser
from pathlib import Path
from typing import Any, Dict, Optional

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
APP_VERSION = "1.8.0"

DEFAULT_CONFIG: Dict[str, Any] = {
    "dashboard_host": "127.0.0.1",
    "dashboard_port": 8765,
    "runtime_dir": "runtime",
}

try:
    import pystray  # type: ignore
    from PIL import Image, ImageDraw  # type: ignore
except Exception:  # pragma: no cover - handled at runtime for user clarity
    pystray = None
    Image = None
    ImageDraw = None


def app_path(value: str, default: str) -> Path:
    raw = str(value or default).strip()
    path = Path(raw)
    return path if path.is_absolute() else BASE_DIR / path


def load_config() -> Dict[str, Any]:
    config = dict(DEFAULT_CONFIG)
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                config.update(data)
        except Exception:
            pass
    return config


def runtime_dir(config: Dict[str, Any]) -> Path:
    path = app_path(config.get("runtime_dir", "runtime"), "runtime")
    path.mkdir(parents=True, exist_ok=True)
    return path


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback
    return fallback


def write_command(config: Dict[str, Any], command: str) -> None:
    allowed = {"arm", "disarm", "toggle_arm", "snapshot", "reload_config", "cleanup_old_files", "quit"}
    if command not in allowed:
        raise ValueError(f"Unsupported command: {command}")
    atomic_write_json(runtime_dir(config) / "command.json", {"command": command, "created_at_epoch": time.time(), "source": "tray"})


def dashboard_url(config: Dict[str, Any]) -> str:
    host = str(config.get("dashboard_host") or "127.0.0.1")
    port = int(config.get("dashboard_port") or 8765)
    return f"http://{host}:{port}"


def python_executable() -> str:
    venv_python = BASE_DIR / ".venv" / "Scripts" / "python.exe"
    if venv_python.exists():
        return str(venv_python)
    return sys.executable


class RoomSentryTray:
    def __init__(self, start_app: bool = True, start_dashboard: bool = True, open_dashboard: bool = False) -> None:
        self.config = load_config()
        self.app_process: Optional[subprocess.Popen[str]] = None
        self.dashboard_process: Optional[subprocess.Popen[str]] = None
        self.icon = None
        if start_dashboard:
            self.start_dashboard()
        if start_app:
            self.start_app()
        if open_dashboard:
            self.open_dashboard()

    def start_app(self) -> None:
        if self.app_process and self.app_process.poll() is None:
            return
        self.app_process = subprocess.Popen(
            [python_executable(), str(BASE_DIR / "room_sentry.py")],
            cwd=str(BASE_DIR),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )

    def start_dashboard(self) -> None:
        if self.dashboard_process and self.dashboard_process.poll() is None:
            return
        self.dashboard_process = subprocess.Popen(
            [python_executable(), str(BASE_DIR / "dashboard_server.py"), "--no-open"],
            cwd=str(BASE_DIR),
            creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
        )

    def open_dashboard(self) -> None:
        webbrowser.open(dashboard_url(load_config()))

    def send(self, command: str) -> None:
        self.config = load_config()
        write_command(self.config, command)

    def state_text(self) -> str:
        config = load_config()
        state = read_json(runtime_dir(config) / "state.json", {})
        armed = "armed" if state.get("armed") else "disarmed"
        room = state.get("room_state") or "unknown"
        updated = float(state.get("updated_at_epoch") or 0)
        age = int(time.time() - updated) if updated else None
        if age is None:
            return "RoomSentry: no runtime state yet"
        return f"RoomSentry: {armed}, {room}, heartbeat {age}s ago"

    def make_icon_image(self):
        if Image is None or ImageDraw is None:
            return None
        img = Image.new("RGBA", (64, 64), (7, 10, 8, 255))
        draw = ImageDraw.Draw(img)
        draw.rounded_rectangle((8, 8, 56, 56), radius=14, fill=(15, 35, 21, 255), outline=(115, 255, 157, 255), width=3)
        draw.ellipse((20, 20, 44, 44), fill=(115, 255, 157, 255))
        draw.ellipse((27, 27, 37, 37), fill=(7, 10, 8, 255))
        return img

    def stop_process(self, proc: Optional[subprocess.Popen[str]]) -> None:
        if not proc or proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)  # type: ignore[attr-defined]
            else:
                proc.terminate()
            proc.wait(timeout=4)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass

    def quit(self, icon=None, item=None) -> None:
        try:
            self.send("quit")
        except Exception:
            pass
        self.stop_process(self.app_process)
        self.stop_process(self.dashboard_process)
        if icon:
            icon.stop()

    def menu(self):
        return pystray.Menu(
            pystray.MenuItem(lambda text: self.state_text(), None, enabled=False),
            pystray.MenuItem("Open dashboard", lambda icon, item: self.open_dashboard()),
            pystray.MenuItem("Arm", lambda icon, item: self.send("arm")),
            pystray.MenuItem("Disarm", lambda icon, item: self.send("disarm")),
            pystray.MenuItem("Take snapshot", lambda icon, item: self.send("snapshot")),
            pystray.MenuItem("Reload config", lambda icon, item: self.send("reload_config")),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Start RoomSentry", lambda icon, item: self.start_app()),
            pystray.MenuItem("Start dashboard server", lambda icon, item: self.start_dashboard()),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Quit RoomSentry + tray", self.quit),
        )

    def run(self) -> None:
        if pystray is None or Image is None:
            print("pystray and pillow are required for tray mode. Run install_windows.ps1 again.")
            print("Manual install: pip install pystray pillow")
            raise SystemExit(2)
        self.icon = pystray.Icon("RoomSentry", self.make_icon_image(), "RoomSentry", self.menu())
        self.icon.run()


def main() -> None:
    parser = argparse.ArgumentParser(description="RoomSentry Windows tray controller")
    parser.add_argument("--no-app", action="store_true", help="Do not start room_sentry.py automatically")
    parser.add_argument("--no-dashboard", action="store_true", help="Do not start dashboard_server.py automatically")
    parser.add_argument("--open-dashboard", action="store_true", help="Open the dashboard when tray starts")
    args = parser.parse_args()
    tray = RoomSentryTray(start_app=not args.no_app, start_dashboard=not args.no_dashboard, open_dashboard=args.open_dashboard)
    tray.run()


if __name__ == "__main__":
    main()
