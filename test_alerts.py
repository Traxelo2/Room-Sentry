import json
import sys
from pathlib import Path

import requests

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"


def load_config():
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def send_discord(config, message):
    url = str(config.get("discord_webhook_url", "")).strip()
    if not url:
        return "Discord skipped: no discord_webhook_url set."
    requests.post(url, json={"content": message}, timeout=15).raise_for_status()
    return "Discord OK."


def send_telegram(config, message):
    token = str(config.get("telegram_bot_token", "")).strip()
    chat_id = str(config.get("telegram_chat_id", "")).strip()
    if not token or not chat_id:
        return "Telegram skipped: no telegram_bot_token/chat_id set."
    requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": message},
        timeout=15,
    ).raise_for_status()
    return "Telegram OK."


def send_ntfy(config, message):
    url = str(config.get("ntfy_url", "")).strip()
    if not url:
        return "ntfy skipped: no ntfy_url set."
    requests.post(url, data=message.encode("utf-8"), headers={"Title": "RoomSentry test"}, timeout=15).raise_for_status()
    return "ntfy OK."


def send_generic(config, message):
    url = str(config.get("generic_webhook_url", "")).strip()
    if not url:
        return "Generic webhook skipped: no generic_webhook_url set."
    requests.post(url, json={"source": "RoomSentry", "message": message, "test": True}, timeout=15).raise_for_status()
    return "Generic webhook OK."


def main():
    config = load_config()
    message = str(config.get("discord_test_message", "RoomSentry test alert"))
    outputs = []
    errors = []
    for fn in [send_discord, send_telegram, send_ntfy, send_generic]:
        try:
            outputs.append(fn(config, "🧪 " + message))
        except Exception as exc:
            errors.append(f"{fn.__name__} failed: {exc}")
    print("\n".join(outputs + errors))
    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
