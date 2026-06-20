import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
EXAMPLE_PATH = BASE_DIR / "config.example.json"

NUMERIC_RANGES = {
    "confidence_threshold": (0.05, 1.0),
    "person_confirm_seconds": (0.0, 30.0),
    "alert_cooldown_seconds": (0, 86400),
    "detection_fps_limit": (0, 60),
    "empty_reset_seconds": (0, 300),
    "dashboard_port": (1, 65535),
    "clip_pre_seconds": (0, 60),
    "clip_post_seconds": (0, 120),
    "auto_delete_days": (1, 3650),
}

SECRET_KEYS = ("token", "webhook", "password", "secret", "key")


def load_config(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError("config must be a JSON object")
    return data


def validate_zone_list(config: Dict[str, Any], key: str, warnings: List[str], errors: List[str]) -> None:
    zones = config.get(key, [])
    if not isinstance(zones, list):
        errors.append(f"{key} must be a list")
        return
    for i, zone in enumerate(zones, start=1):
        if not isinstance(zone, dict):
            errors.append(f"{key}[{i}] must be an object")
            continue
        for point in ("x1", "y1", "x2", "y2"):
            if point not in zone:
                errors.append(f"{key}[{i}].{point} is missing")
                continue
            try:
                float(zone[point])
            except Exception:
                errors.append(f"{key}[{i}].{point} must be numeric")
        if key == "privacy_zones" and str(zone.get("mode", "blur")).lower() not in {"blur", "black", "blackout"}:
            warnings.append(f"{key}[{i}].mode should be blur, black, or blackout")


def redacted(config: Dict[str, Any]) -> Dict[str, Any]:
    output = {}
    for key, value in config.items():
        if any(word in key.lower() for word in SECRET_KEYS) and value:
            output[key] = "***set***"
        else:
            output[key] = value
    return output


def validate(config: Dict[str, Any]) -> Dict[str, Any]:
    errors: List[str] = []
    warnings: List[str] = []

    for key, (lo, hi) in NUMERIC_RANGES.items():
        if key not in config:
            warnings.append(f"{key} is missing; migration will add it from defaults")
            continue
        try:
            value = float(config[key])
        except Exception:
            errors.append(f"{key} must be numeric")
            continue
        if not (lo <= value <= hi):
            errors.append(f"{key}={value} is outside expected range {lo}-{hi}")

    host = str(config.get("dashboard_host", "127.0.0.1"))
    if host not in {"127.0.0.1", "localhost"}:
        warnings.append("dashboard_host is not localhost; do not expose RoomSentry publicly")

    validate_zone_list(config, "ignore_zones", warnings, errors)
    validate_zone_list(config, "privacy_zones", warnings, errors)

    if config.get("save_clips") and not config.get("apply_privacy_zones_to_clips", True):
        warnings.append("save_clips is enabled but privacy zones are not applied to clips")

    if config.get("send_snapshot_to_discord") and config.get("discord_webhook_url") and not config.get("blur_saved_snapshots"):
        warnings.append("Discord snapshots are enabled; consider blur_saved_snapshots or privacy_zones")

    return {"ok": not errors, "errors": errors, "warnings": warnings, "config": redacted(config)}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate RoomSentry config")
    parser.add_argument("--example", action="store_true", help="Validate config.example.json instead of config.json")
    parser.add_argument("--json", action="store_true", help="Output JSON")
    args = parser.parse_args()

    path = EXAMPLE_PATH if args.example else CONFIG_PATH
    if not path.exists():
        raise SystemExit(f"Missing {path.name}. Run python migrate_config.py first.")
    result = validate(load_config(path))

    if args.json:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print("RoomSentry Config Validation")
        print("Result:", "PASS" if result["ok"] else "FAIL")
        for msg in result["errors"]:
            print("[ERROR]", msg)
        for msg in result["warnings"]:
            print("[WARN] ", msg)
    sys.exit(0 if result["ok"] else 1)


if __name__ == "__main__":
    main()
