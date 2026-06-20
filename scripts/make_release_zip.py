"""Create a clean RoomSentry source zip without private/runtime files."""
from __future__ import annotations

import fnmatch
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "dist"
OUT = DIST / "RoomSentry_v1_8_open_source.zip"

EXCLUDE_PATTERNS = [
    ".git/*",
    "venv/*",
    ".venv/*",
    "__pycache__/*",
    "*/__pycache__/*",
    "config.json",
    ".env",
    ".env.*",
    "snapshots/*",
    "clips/*",
    "logs/*",
    "events/*",
    "runtime/*",
    "exports/*",
    "*.sqlite3",
    "*.db",
    "*.jsonl",
    "*.pt",
    "*.mp4",
    "*.avi",
    "*.mov",
    "*.mkv",
    "*.zip",
]


def excluded(path: Path) -> bool:
    rel = path.relative_to(ROOT).as_posix()
    return any(fnmatch.fnmatch(rel, pattern) for pattern in EXCLUDE_PATTERNS)


def main() -> None:
    DIST.mkdir(exist_ok=True)
    if OUT.exists():
        OUT.unlink()
    with zipfile.ZipFile(OUT, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in sorted(ROOT.rglob("*")):
            if path.is_dir() or excluded(path):
                continue
            zf.write(path, Path("RoomSentry") / path.relative_to(ROOT))
    print(OUT)


if __name__ == "__main__":
    main()
