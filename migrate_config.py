import ast
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
ROOM_SENTRY_PATH = BASE_DIR / "room_sentry.py"


def load_default_config():
    tree = ast.parse(ROOM_SENTRY_PATH.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", None) == "DEFAULT_CONFIG":
            return ast.literal_eval(node.value)
    raise RuntimeError("Could not find DEFAULT_CONFIG in room_sentry.py")


def migrate():
    default_config = load_default_config()
    example_path = BASE_DIR / "config.example.json"
    config_path = BASE_DIR / "config.json"
    example_path.write_text(json.dumps(default_config, indent=4), encoding="utf-8")

    if config_path.exists():
        try:
            current_config = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(current_config, dict):
                current_config = {}
        except json.JSONDecodeError:
            backup = config_path.with_suffix(".json.bad")
            config_path.replace(backup)
            print(f"Bad config backed up to {backup.name}")
            current_config = {}
    else:
        current_config = {}

    changed = False
    for key, value in default_config.items():
        if key not in current_config:
            current_config[key] = value
            changed = True

    config_path.write_text(json.dumps(current_config, indent=4), encoding="utf-8")
    print("config.json migrated successfully." if changed else "config.json is already up to date.")


if __name__ == "__main__":
    migrate()
