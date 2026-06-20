import argparse
import html
import json
import mimetypes
import sqlite3
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, Dict, List

BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
APP_VERSION = "1.8.0"

DEFAULT_CONFIG = {
    "events_db_path": "events/roomsentry_events.sqlite3",
    "runtime_dir": "runtime",
    "dashboard_host": "127.0.0.1",
    "dashboard_port": 8765,
    "dashboard_command_token": "",
    "heartbeat_timeout_seconds": 8,
    "privacy_zones": [],
    "ignore_zones": [],
    "dashboard_host": "127.0.0.1",
}


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


def runtime_file(config: Dict[str, Any], name: str) -> Path:
    runtime_dir = app_path(config.get("runtime_dir", "runtime"), "runtime")
    runtime_dir.mkdir(parents=True, exist_ok=True)
    return runtime_dir / name


def atomic_write_json(path: Path, payload: Dict[str, Any]) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path, fallback: Dict[str, Any]) -> Dict[str, Any]:
    try:
        if path.exists():
            data = json.loads(path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else fallback
    except Exception:
        return fallback
    return fallback


def event_db_path(config: Dict[str, Any]) -> Path:
    return app_path(config.get("events_db_path", "events/roomsentry_events.sqlite3"), "events/roomsentry_events.sqlite3")


def ensure_event_review_schema(config: Dict[str, Any]) -> None:
    """Add v1.8 review columns to older event databases without breaking them."""
    db = event_db_path(config)
    db.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(db) as conn:
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
        columns = {
            "important": "INTEGER DEFAULT 0",
            "false_positive": "INTEGER DEFAULT 0",
            "review_note": "TEXT DEFAULT ''",
            "reviewed_at": "TEXT",
        }
        for name, ddl in columns.items():
            if name not in existing:
                conn.execute(f"ALTER TABLE events ADD COLUMN {name} {ddl}")
        conn.commit()


def fetch_events(config: Dict[str, Any], limit: int = 100, filters: Dict[str, str] | None = None) -> List[Dict[str, Any]]:
    db = event_db_path(config)
    if not db.exists():
        return []
    ensure_event_review_schema(config)
    filters = filters or {}
    limit = max(1, min(limit, 1000))
    where = []
    params: List[Any] = []
    event_type = filters.get("type", "").strip()
    if event_type:
        where.append("event_type = ?")
        params.append(event_type)
    search = filters.get("q", "").strip()
    if search:
        where.append("(message LIKE ? OR event_type LIKE ? OR review_note LIKE ?)")
        like = f"%{search}%"
        params.extend([like, like, like])
    if filters.get("important") == "1":
        where.append("COALESCE(important, 0) = 1")
    if filters.get("false_positive") == "1":
        where.append("COALESCE(false_positive, 0) = 1")
    if filters.get("has_snapshot") == "1":
        where.append("snapshot_path IS NOT NULL AND snapshot_path != ''")
    if filters.get("has_clip") == "1":
        where.append("clip_path IS NOT NULL AND clip_path != ''")
    date = filters.get("date", "").strip()
    if date:
        where.append("substr(created_at, 1, 10) = ?")
        params.append(date[:10])
    sql = "SELECT * FROM events"
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY id DESC LIMIT ?"
    params.append(limit)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(sql, params).fetchall()
    out = []
    for row in rows:
        item = dict(row)
        try:
            item["payload"] = json.loads(item.get("payload_json") or "{}")
        except Exception:
            item["payload"] = {}
        item.pop("payload_json", None)
        item["important"] = bool(item.get("important"))
        item["false_positive"] = bool(item.get("false_positive"))
        out.append(item)
    return out


def daily_summary(config: Dict[str, Any], date: str = "") -> Dict[str, Any]:
    db = event_db_path(config)
    if not db.exists():
        return {"ok": True, "date": date or time.strftime("%Y-%m-%d"), "total": 0, "by_type": {}, "important": 0, "false_positive": 0, "snapshots": 0, "clips": 0}
    ensure_event_review_schema(config)
    date = (date or time.strftime("%Y-%m-%d"))[:10]
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute("SELECT * FROM events WHERE substr(created_at,1,10)=?", (date,)).fetchall()
    by_type: Dict[str, int] = {}
    important = false_positive = snapshots = clips = 0
    for row in rows:
        by_type[row["event_type"]] = by_type.get(row["event_type"], 0) + 1
        important += int(row["important"] or 0)
        false_positive += int(row["false_positive"] or 0)
        snapshots += 1 if row["snapshot_path"] else 0
        clips += 1 if row["clip_path"] else 0
    return {"ok": True, "date": date, "total": len(rows), "by_type": by_type, "important": important, "false_positive": false_positive, "snapshots": snapshots, "clips": clips}


def update_event_review(config: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    db = event_db_path(config)
    if not db.exists():
        return {"ok": False, "message": "Event database not found"}
    ensure_event_review_schema(config)
    try:
        event_id = int(data.get("id"))
    except Exception:
        return {"ok": False, "message": "Missing valid event id"}
    fields = []
    params: List[Any] = []
    if "important" in data:
        fields.append("important = ?")
        params.append(1 if data.get("important") else 0)
    if "false_positive" in data:
        fields.append("false_positive = ?")
        params.append(1 if data.get("false_positive") else 0)
    if "review_note" in data:
        fields.append("review_note = ?")
        params.append(str(data.get("review_note") or "")[:500])
    if not fields:
        return {"ok": False, "message": "No review fields supplied"}
    fields.append("reviewed_at = ?")
    params.append(time.strftime("%Y-%m-%dT%H:%M:%S"))
    params.append(event_id)
    with sqlite3.connect(db) as conn:
        cur = conn.execute(f"UPDATE events SET {', '.join(fields)} WHERE id = ?", params)
        conn.commit()
    return {"ok": cur.rowcount > 0, "message": "Event review updated" if cur.rowcount else "Event not found", "id": event_id}


def delete_events(config: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    db = event_db_path(config)
    if not db.exists():
        return {"ok": False, "message": "Event database not found"}
    ids_raw = data.get("ids", [])
    if not isinstance(ids_raw, list) or not ids_raw:
        return {"ok": False, "message": "ids must be a non-empty array"}
    ids = []
    for value in ids_raw[:200]:
        try:
            ids.append(int(value))
        except Exception:
            pass
    if not ids:
        return {"ok": False, "message": "No valid event ids"}
    delete_media = bool(data.get("delete_media"))
    media_paths: List[Path] = []
    ensure_event_review_schema(config)
    with sqlite3.connect(db) as conn:
        conn.row_factory = sqlite3.Row
        placeholders = ",".join("?" for _ in ids)
        rows = conn.execute(f"SELECT snapshot_path, clip_path FROM events WHERE id IN ({placeholders})", ids).fetchall()
        if delete_media:
            for row in rows:
                for key in ("snapshot_path", "clip_path"):
                    rel = row[key]
                    if rel:
                        try:
                            media_paths.append(safe_media_path(rel))
                        except Exception:
                            pass
        cur = conn.execute(f"DELETE FROM events WHERE id IN ({placeholders})", ids)
        conn.commit()
    removed_files = 0
    if delete_media:
        for path in media_paths:
            try:
                path.unlink(missing_ok=True)
                removed_files += 1
            except Exception:
                pass
    return {"ok": True, "deleted_events": cur.rowcount, "deleted_media_files": removed_files}



def latest_ack(config: Dict[str, Any]) -> Dict[str, Any]:
    return read_json(runtime_file(config, "last_command_ack.json"), {})


def current_state(config: Dict[str, Any]) -> Dict[str, Any]:
    state = read_json(
        runtime_file(config, "state.json"),
        {
            "running": False,
            "armed": False,
            "room_state": "UNKNOWN",
            "camera_ok": False,
            "message": "RoomSentry has not written runtime state yet.",
        },
    )
    updated_epoch = float(state.get("updated_at_epoch") or 0)
    stale_after = float(config.get("heartbeat_timeout_seconds", 8))
    state["heartbeat_age_seconds"] = round(max(0, time.time() - updated_epoch), 1) if updated_epoch else None
    state["stale"] = bool(updated_epoch and (time.time() - updated_epoch > stale_after)) or not updated_epoch
    state["ack"] = latest_ack(config)
    return state



def redacted_config(config: Dict[str, Any]) -> Dict[str, Any]:
    secret_words = ("token", "webhook", "password", "secret", "key")
    out: Dict[str, Any] = {}
    for key, value in config.items():
        if any(word in key.lower() for word in secret_words) and value:
            out[key] = "***set***"
        else:
            out[key] = value
    return out


def normalize_zone(zone: Dict[str, Any], fallback_name: str = "zone", include_mode: bool = False) -> Dict[str, Any]:
    """Validate and normalise a dashboard-edited zone.

    Coordinates are stored as normalized 0.0-1.0 values so they work across
    different camera resolutions.
    """
    def clamp(value: Any) -> float:
        try:
            return max(0.0, min(1.0, float(value)))
        except Exception:
            return 0.0

    x1 = clamp(zone.get("x1", 0.0))
    y1 = clamp(zone.get("y1", 0.0))
    x2 = clamp(zone.get("x2", 0.0))
    y2 = clamp(zone.get("y2", 0.0))
    left, right = sorted([x1, x2])
    top, bottom = sorted([y1, y2])
    if right - left < 0.01 or bottom - top < 0.01:
        raise ValueError("Zone is too small. Draw a larger box.")
    name = str(zone.get("name") or fallback_name).strip()[:80]
    out: Dict[str, Any] = {
        "name": name,
        "x1": round(left, 4),
        "y1": round(top, 4),
        "x2": round(right, 4),
        "y2": round(bottom, 4),
    }
    if include_mode:
        mode = str(zone.get("mode", "blur")).strip().lower()
        if mode == "black":
            mode = "blackout"
        out["mode"] = mode if mode in {"blur", "blackout"} else "blur"
        if "blur_kernel" in zone:
            try:
                kernel = int(zone.get("blur_kernel") or 51)
                if kernel % 2 == 0:
                    kernel += 1
                out["blur_kernel"] = max(3, min(151, kernel))
            except Exception:
                pass
    return out


def zones_payload(config: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "ok": True,
        "ignore_zones": config.get("ignore_zones", []) if isinstance(config.get("ignore_zones", []), list) else [],
        "privacy_zones": config.get("privacy_zones", []) if isinstance(config.get("privacy_zones", []), list) else [],
        "preview_hint": "Draw zones on the latest camera preview, then save. Use Reload Config or the dashboard save button to apply them.",
    }


def save_config_with_backup(config: Dict[str, Any], updates: Dict[str, Any]) -> Path:
    existing: Dict[str, Any] = {}
    if CONFIG_PATH.exists():
        try:
            loaded = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(loaded, dict):
                existing = loaded
        except Exception:
            existing = {}
    merged = dict(config)
    merged.update(existing)
    merged.update(updates)
    if CONFIG_PATH.exists():
        backup = CONFIG_PATH.with_name(f"config.backup.{time.strftime('%Y%m%d-%H%M%S')}.json")
        backup.write_text(CONFIG_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    atomic_write_json(CONFIG_PATH, merged)
    return CONFIG_PATH


def save_zones(config: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    ignore_raw = data.get("ignore_zones", [])
    privacy_raw = data.get("privacy_zones", [])
    if not isinstance(ignore_raw, list) or not isinstance(privacy_raw, list):
        return {"ok": False, "message": "ignore_zones and privacy_zones must be arrays"}
    if len(ignore_raw) > 50 or len(privacy_raw) > 50:
        return {"ok": False, "message": "Too many zones. Limit is 50 per type."}
    try:
        ignore_zones = [normalize_zone(z, f"ignore {i+1}", include_mode=False) for i, z in enumerate(ignore_raw) if isinstance(z, dict)]
        privacy_zones = [normalize_zone(z, f"privacy {i+1}", include_mode=True) for i, z in enumerate(privacy_raw) if isinstance(z, dict)]
    except ValueError as exc:
        return {"ok": False, "message": str(exc)}
    save_config_with_backup(config, {"ignore_zones": ignore_zones, "privacy_zones": privacy_zones})
    write_command(config, "reload_config")
    return {
        "ok": True,
        "message": "Saved zones to config.json and queued config reload.",
        "ignore_zones": ignore_zones,
        "privacy_zones": privacy_zones,
    }


def diagnostics(config: Dict[str, Any]) -> Dict[str, Any]:
    state = current_state(config)
    db = event_db_path(config)
    event_count = 0
    if db.exists():
        try:
            with sqlite3.connect(db) as conn:
                event_count = int(conn.execute("SELECT COUNT(*) FROM events").fetchone()[0])
        except Exception:
            event_count = -1
    return {
        "app": "RoomSentry",
        "dashboard_version": APP_VERSION,
        "state": state,
        "event_count": event_count,
        "database_exists": db.exists(),
        "database_path": str(db.relative_to(BASE_DIR)) if db.exists() else str(db),
        "privacy_zones": len(config.get("privacy_zones", []) or []),
        "ignore_zones": len(config.get("ignore_zones", []) or []),
        "config": redacted_config(config),
    }


def safe_media_path(rel: str) -> Path:
    decoded = urllib.parse.unquote(rel).replace("\\", "/")
    path = (BASE_DIR / decoded).resolve()
    base = BASE_DIR.resolve()
    if base not in [path, *path.parents]:
        raise ValueError("Unsafe media path")
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(decoded)
    return path


def write_command(config: Dict[str, Any], command: str) -> Dict[str, Any]:
    allowed = {"arm", "disarm", "toggle_arm", "snapshot", "reload_config", "cleanup_old_files", "quit"}
    if command not in allowed:
        return {"ok": False, "message": f"Command not allowed: {command}"}
    payload = {"command": command, "created_at_epoch": time.time()}
    atomic_write_json(runtime_file(config, "command.json"), payload)
    return {"ok": True, "message": f"Queued command: {command}", "command": command}


INDEX_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width,initial-scale=1" />
<title>RoomSentry Control</title>
<style>
:root { color-scheme: dark; --bg:#070a08; --panel:#0f1712; --line:#1e3b2b; --soft:#9cc9ad; --text:#eafff2; --lime:#73ff9d; --warn:#ffd36e; --bad:#ff7b7b; }
* { box-sizing:border-box; }
body { margin:0; font-family: Inter, Segoe UI, Arial, sans-serif; background: radial-gradient(circle at top left,#112219,#070a08 55%); color:var(--text); }
header { padding:26px 28px; border-bottom:1px solid var(--line); background:rgba(7,10,8,.78); position:sticky; top:0; z-index:10; backdrop-filter: blur(12px); }
h1 { margin:0; font-size:32px; letter-spacing:-1px; }
p { color:var(--soft); }
main { padding:22px 28px 40px; max-width:1300px; margin:0 auto; }
.grid { display:grid; grid-template-columns: repeat(12,1fr); gap:14px; }
.card { background:rgba(15,23,18,.92); border:1px solid var(--line); border-radius:18px; padding:18px; box-shadow:0 18px 40px rgba(0,0,0,.22); }
.span3 { grid-column:span 3; } .span4 { grid-column:span 4; } .span5 { grid-column:span 5; } .span7 { grid-column:span 7; } .span8 { grid-column:span 8; } .span12 { grid-column:span 12; }
@media(max-width:900px){ .span3,.span4,.span5,.span7,.span8,.span12{ grid-column:span 12; } }
.label { font-size:12px; text-transform:uppercase; letter-spacing:.12em; color:#77a889; }
.big { font-size:30px; font-weight:800; margin-top:8px; }
.good { color:var(--lime); } .warn { color:var(--warn); } .bad { color:var(--bad); }
button { border:1px solid #2e6242; background:#102417; color:var(--text); border-radius:12px; padding:11px 13px; font-weight:700; cursor:pointer; margin:3px; }
button:hover { border-color:var(--lime); }
button.primary { background:#184b2a; border-color:#53c875; }
button.danger { background:#3d1717; border-color:#8f3a3a; }
.preview { width:100%; max-height:430px; object-fit:contain; border-radius:14px; background:#050705; border:1px solid var(--line); }
.tablewrap { overflow:auto; border:1px solid var(--line); border-radius:14px; }
table { width:100%; min-width:920px; border-collapse:collapse; background:#0b110d; }
th,td { padding:11px; border-bottom:1px solid #17271d; text-align:left; vertical-align:top; font-size:14px; }
th { color:#bfffd1; background:#102016; position:sticky; top:0; }
a { color:var(--lime); }
.badge { display:inline-block; padding:4px 8px; border:1px solid #2f6041; border-radius:999px; background:#0d1a12; color:#bfffd1; font-size:12px; }
.gallery { display:grid; grid-template-columns:repeat(auto-fill,minmax(150px,1fr)); gap:12px; }
figure { margin:0; border:1px solid var(--line); border-radius:14px; overflow:hidden; background:#0c120e; }
figure img { width:100%; height:116px; object-fit:cover; display:block; }
figcaption { padding:8px; color:var(--soft); font-size:11px; }
.code { font-family:Consolas,monospace; white-space:pre-wrap; background:#050805; border:1px solid var(--line); border-radius:12px; padding:10px; color:#c9f7d6; }

.previewWrap { position:relative; display:inline-block; width:100%; }
#zoneCanvas { position:absolute; left:0; top:0; width:100%; height:100%; cursor:crosshair; touch-action:none; }
.zoneTools { display:flex; gap:10px; flex-wrap:wrap; align-items:center; margin:10px 0 12px; }
.zoneTools label { color:var(--soft); font-size:13px; display:flex; gap:6px; align-items:center; }
select,input { background:#07100b; color:var(--text); border:1px solid #2e6242; border-radius:10px; padding:9px; }
.toolbar { display:flex; gap:10px; align-items:center; flex-wrap:wrap; margin:10px 0 14px; }
.toolbar label { color:var(--soft); font-size:13px; display:flex; gap:6px; align-items:center; }
.muted { color:var(--soft); font-size:13px; }
.rowImportant { background:rgba(255,211,110,.08); }
.rowFalsePositive { opacity:.62; }
.actions button { padding:7px 8px; font-size:12px; }
.zoneLists { display:grid; grid-template-columns:1fr 1fr; gap:14px; }
.zoneLists ol { margin:8px 0 0; padding-left:22px; color:#d9ffe5; }
.zoneLists li { margin:6px 0; color:#bfe8cc; }
@media(max-width:900px){ .zoneLists{ grid-template-columns:1fr; } }
</style>
</head>
<body>
<header>
  <h1>RoomSentry Control</h1>
  <p>Local-only dashboard. Keep host as 127.0.0.1 unless you know exactly what you’re doing.</p>
</header>
<main>
  <div class="grid">
    <section class="card span3"><div class="label">Runtime</div><div id="running" class="big">Loading</div></section>
    <section class="card span3"><div class="label">Armed</div><div id="armed" class="big">Loading</div></section>
    <section class="card span3"><div class="label">Room</div><div id="room" class="big">Loading</div></section>
    <section class="card span3"><div class="label">Detector FPS</div><div id="fps" class="big">—</div></section>

    <section class="card span5">
      <div class="label">Controls</div>
      <p id="message">Loading status…</p>
      <button class="primary" onclick="sendCommand('arm')">Arm</button>
      <button onclick="sendCommand('disarm')">Disarm</button>
      <button onclick="sendCommand('toggle_arm')">Toggle</button>
      <button onclick="sendCommand('snapshot')">Snapshot</button>
      <button onclick="sendCommand('reload_config')">Reload Config</button>
      <button onclick="sendCommand('cleanup_old_files')">Cleanup Old Files</button>
      <button class="danger" onclick="sendCommand('quit')">Quit App</button>
      <div id="ack" class="code" style="margin-top:12px">No command sent yet.</div>
    </section>

    <section class="card span7">
      <div class="label">Latest camera preview</div>
      <p>Updates every few seconds while RoomSentry is running.</p>
      <div class="previewWrap">
        <img id="preview" class="preview" alt="Latest frame" />
        <canvas id="zoneCanvas"></canvas>
      </div>
    </section>

    <section class="card span12">
      <div class="label">Visual Zone Editor</div>
      <p>Draw on the camera preview. Ignore zones suppress detections. Privacy zones blur or black out sensitive areas in previews, snapshots, and clips.</p>
      <div class="zoneTools">
        <label>Type <select id="zoneKind"><option value="ignore">Ignore zone</option><option value="privacy">Privacy zone</option></select></label>
        <label>Privacy mode <select id="zoneMode"><option value="blur">Blur</option><option value="blackout">Blackout</option></select></label>
        <label>Name <input id="zoneName" placeholder="door, window, bed, monitor" /></label>
        <button onclick="undoZone()">Undo</button>
        <button onclick="clearDraftZones()">Clear Draft</button>
        <button class="primary" onclick="saveZones()">Save Zones</button>
        <button onclick="loadZones()">Reload Zones</button>
      </div>
      <div id="zoneStatus" class="code">Load the preview, then drag boxes on it.</div>
      <div class="zoneLists">
        <div><h3>Ignore zones</h3><ol id="ignoreZones"></ol></div>
        <div><h3>Privacy zones</h3><ol id="privacyZones"></ol></div>
      </div>
    </section>

    <section class="card span12">
      <div class="label">Diagnostics</div>
      <p>Redacted local config and health summary. Secrets are never shown here.</p>
      <button onclick="loadDiagnostics()">Refresh Diagnostics</button>
      <pre id="diagnostics" class="code">Not loaded yet.</pre>
    </section>

    <section class="card span12">
      <div class="label">Snapshot Gallery</div>
      <div id="gallery" class="gallery"></div>
    </section>

    <section class="card span12">
      <div class="label">Event Review/Search</div>
      <p>Search, filter, mark important, mark false positives, and clean up selected events.</p>
      <div class="toolbar">
        <label>Search <input id="eventSearch" placeholder="person, snapshot, note…" /></label>
        <label>Type <select id="eventType"><option value="">All</option><option value="person_detected">person_detected</option><option value="manual_snapshot">manual_snapshot</option><option value="system">system</option></select></label>
        <label>Date <input id="eventDate" type="date" /></label>
        <label><input id="filterImportant" type="checkbox" /> Important</label>
        <label><input id="filterFalsePositive" type="checkbox" /> False positives</label>
        <label><input id="filterSnapshots" type="checkbox" /> Has snapshot</label>
        <label><input id="filterClips" type="checkbox" /> Has clip</label>
        <button onclick="refresh()">Apply</button>
        <button onclick="clearEventFilters()">Clear</button>
      </div>
      <div class="toolbar">
        <button class="primary" onclick="exportVisibleEvents()">Export visible JSON</button>
        <button onclick="loadDailySummary()">Daily summary</button>
        <button class="danger" onclick="deleteSelected(false)">Delete selected rows</button>
        <button class="danger" onclick="deleteSelected(true)">Delete selected + media</button>
        <span id="selectedCount" class="muted">0 selected</span>
      </div>
      <pre id="eventSummary" class="code">No summary loaded yet.</pre>
      <div class="tablewrap"><table>
        <thead><tr><th><input type="checkbox" id="selectAllEvents" onclick="toggleSelectAll(this.checked)"></th><th>Time</th><th>Type</th><th>Message</th><th>Review</th><th>Conf</th><th>People</th><th>Snapshot</th><th>Clip</th><th>Actions</th></tr></thead>
        <tbody id="events"><tr><td colspan="10">Loading…</td></tr></tbody>
      </table></div>
    </section>
  </div>
</main>
<script>
const esc = (s) => String(s ?? '').replace(/[&<>'"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));
const media = (path) => path ? '/media/' + encodeURI(path).replace(/#/g,'%23') : '';
let ignoreZones = [];
let privacyZones = [];
let drawing = false;
let dragStart = null;
let draftZone = null;
let currentEvents = [];
let selectedEvents = new Set();

function setBig(id, value, cls='') { const el=document.getElementById(id); el.textContent=value; el.className='big '+cls; }
function activeZones() { return [...ignoreZones.map(z=>({...z, kind:'ignore'})), ...privacyZones.map(z=>({...z, kind:'privacy'}))]; }
function canvasEls() { return { img: document.getElementById('preview'), canvas: document.getElementById('zoneCanvas') }; }
function resizeCanvasToImage() {
  const {img, canvas} = canvasEls();
  const rect = img.getBoundingClientRect();
  canvas.width = Math.max(1, Math.round(rect.width));
  canvas.height = Math.max(1, Math.round(rect.height));
  canvas.style.width = rect.width + 'px';
  canvas.style.height = rect.height + 'px';
  drawCanvas();
}
function pointerNorm(ev) {
  const {canvas} = canvasEls();
  const rect = canvas.getBoundingClientRect();
  const x = Math.max(0, Math.min(1, (ev.clientX - rect.left) / Math.max(1, rect.width)));
  const y = Math.max(0, Math.min(1, (ev.clientY - rect.top) / Math.max(1, rect.height)));
  return {x,y};
}
function zoneLabel(z, i) {
  const type = z.kind === 'privacy' ? `privacy/${z.mode || 'blur'}` : 'ignore';
  return `${i+1}. ${z.name || type} (${type}) ${Number(z.x1).toFixed(2)},${Number(z.y1).toFixed(2)} → ${Number(z.x2).toFixed(2)},${Number(z.y2).toFixed(2)}`;
}
function drawOne(ctx, z, isDraft=false) {
  const {canvas} = canvasEls();
  const x = Math.min(z.x1,z.x2) * canvas.width;
  const y = Math.min(z.y1,z.y2) * canvas.height;
  const w = Math.abs(z.x2-z.x1) * canvas.width;
  const h = Math.abs(z.y2-z.y1) * canvas.height;
  const privacy = z.kind === 'privacy';
  ctx.save();
  ctx.lineWidth = isDraft ? 3 : 2;
  ctx.strokeStyle = privacy ? '#ffd36e' : '#73ff9d';
  ctx.fillStyle = privacy ? 'rgba(255,211,110,.18)' : 'rgba(115,255,157,.14)';
  if (z.mode === 'blackout') ctx.fillStyle = 'rgba(0,0,0,.45)';
  ctx.fillRect(x,y,w,h); ctx.strokeRect(x,y,w,h);
  ctx.font = '12px Segoe UI, Arial';
  ctx.fillStyle = privacy ? '#ffd36e' : '#73ff9d';
  ctx.fillText(z.name || (privacy ? 'privacy' : 'ignore'), x+6, Math.max(14,y+16));
  ctx.restore();
}
function drawCanvas() {
  const {canvas} = canvasEls();
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0,0,canvas.width,canvas.height);
  activeZones().forEach(z => drawOne(ctx,z));
  if (draftZone) drawOne(ctx,draftZone,true);
}
function renderZoneLists() {
  document.getElementById('ignoreZones').innerHTML = ignoreZones.length ? ignoreZones.map((z,i)=>`<li>${esc(zoneLabel({...z,kind:'ignore'},i))}</li>`).join('') : '<li>No ignore zones.</li>';
  document.getElementById('privacyZones').innerHTML = privacyZones.length ? privacyZones.map((z,i)=>`<li>${esc(zoneLabel({...z,kind:'privacy'},i))}</li>`).join('') : '<li>No privacy zones.</li>';
  const total = ignoreZones.length + privacyZones.length;
  document.getElementById('zoneStatus').textContent = `${total} zone(s) loaded. Drag on the preview to add another zone, then Save Zones.`;
  drawCanvas();
}
function addDraftToZones(z) {
  const width = Math.abs(z.x2 - z.x1), height = Math.abs(z.y2 - z.y1);
  if (width < 0.01 || height < 0.01) { document.getElementById('zoneStatus').textContent = 'Zone too small; draw a larger box.'; return; }
  const kind = document.getElementById('zoneKind').value;
  const name = document.getElementById('zoneName').value.trim() || `${kind} ${kind === 'ignore' ? ignoreZones.length + 1 : privacyZones.length + 1}`;
  const base = {name, x1:Math.min(z.x1,z.x2), y1:Math.min(z.y1,z.y2), x2:Math.max(z.x1,z.x2), y2:Math.max(z.y1,z.y2)};
  if (kind === 'privacy') privacyZones.push({...base, mode:document.getElementById('zoneMode').value});
  else ignoreZones.push(base);
  renderZoneLists();
}
function undoZone() {
  if (privacyZones.length && document.getElementById('zoneKind').value === 'privacy') privacyZones.pop();
  else if (ignoreZones.length) ignoreZones.pop();
  else if (privacyZones.length) privacyZones.pop();
  renderZoneLists();
}
function clearDraftZones() { ignoreZones=[]; privacyZones=[]; draftZone=null; renderZoneLists(); }
async function loadZones() {
  const res = await fetch('/api/zones');
  const data = await res.json();
  ignoreZones = Array.isArray(data.ignore_zones) ? data.ignore_zones : [];
  privacyZones = Array.isArray(data.privacy_zones) ? data.privacy_zones : [];
  renderZoneLists();
}
async function saveZones() {
  const res = await fetch('/api/zones', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({ignore_zones:ignoreZones, privacy_zones:privacyZones})});
  const data = await res.json();
  document.getElementById('zoneStatus').textContent = JSON.stringify(data, null, 2);
  if (data.ok) { ignoreZones=data.ignore_zones || []; privacyZones=data.privacy_zones || []; renderZoneLists(); setTimeout(refresh, 500); }
}
async function sendCommand(command) {
  const res = await fetch('/api/command', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({command})});
  const data = await res.json();
  document.getElementById('ack').textContent = JSON.stringify(data, null, 2);
  setTimeout(refresh, 500);
}
async function loadDiagnostics() {
  const res = await fetch('/api/diagnostics');
  const data = await res.json();
  document.getElementById('diagnostics').textContent = JSON.stringify(data, null, 2);
}
function eventQuery() {
  const params = new URLSearchParams({limit:'250'});
  const q = document.getElementById('eventSearch')?.value.trim(); if (q) params.set('q', q);
  const type = document.getElementById('eventType')?.value; if (type) params.set('type', type);
  const date = document.getElementById('eventDate')?.value; if (date) params.set('date', date);
  if (document.getElementById('filterImportant')?.checked) params.set('important', '1');
  if (document.getElementById('filterFalsePositive')?.checked) params.set('false_positive', '1');
  if (document.getElementById('filterSnapshots')?.checked) params.set('has_snapshot', '1');
  if (document.getElementById('filterClips')?.checked) params.set('has_clip', '1');
  return params.toString();
}
function clearEventFilters() {
  ['eventSearch','eventType','eventDate'].forEach(id => { const el=document.getElementById(id); if(el) el.value=''; });
  ['filterImportant','filterFalsePositive','filterSnapshots','filterClips'].forEach(id => { const el=document.getElementById(id); if(el) el.checked=false; });
  refresh();
}
function updateSelectedCount(){ document.getElementById('selectedCount').textContent = `${selectedEvents.size} selected`; }
function toggleEventSelected(id, checked){ checked ? selectedEvents.add(Number(id)) : selectedEvents.delete(Number(id)); updateSelectedCount(); }
function toggleSelectAll(checked){ currentEvents.forEach(e => checked ? selectedEvents.add(Number(e.id)) : selectedEvents.delete(Number(e.id))); renderEvents(currentEvents); }
function reviewText(e){
  const parts=[]; if(e.important) parts.push('⭐ important'); if(e.false_positive) parts.push('false positive'); if(e.review_note) parts.push(e.review_note); return parts.join(' · ');
}
function renderEvents(events){
  const tbody = document.getElementById('events');
  tbody.innerHTML = events.length ? events.map(e => `<tr class="${e.important?'rowImportant':''} ${e.false_positive?'rowFalsePositive':''}">
    <td><input type="checkbox" ${selectedEvents.has(Number(e.id))?'checked':''} onchange="toggleEventSelected(${Number(e.id)}, this.checked)"></td>
    <td>${esc(e.created_at)}</td><td><span class="badge">${esc(e.event_type)}</span></td><td>${esc(e.message)}</td>
    <td>${esc(reviewText(e))}</td><td>${e.confidence == null ? '' : Number(e.confidence).toFixed(3)}</td><td>${e.person_count ?? ''}</td>
    <td>${e.snapshot_path ? `<a href="${media(e.snapshot_path)}" target="_blank">open</a>` : ''}</td>
    <td>${e.clip_path ? `<a href="${media(e.clip_path)}" target="_blank">open</a>` : ''}</td>
    <td class="actions"><button onclick="markEvent(${Number(e.id)}, 'important', ${e.important ? 'false':'true'})">⭐</button><button onclick="markEvent(${Number(e.id)}, 'false_positive', ${e.false_positive ? 'false':'true'})">Wrong</button><button onclick="noteEvent(${Number(e.id)})">Note</button></td>
  </tr>`).join('') : '<tr><td colspan="10">No matching events.</td></tr>';
  updateSelectedCount();
}
async function markEvent(id, field, value){
  const res = await fetch('/api/events/review', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({id, [field]: value})});
  const data = await res.json(); document.getElementById('eventSummary').textContent = JSON.stringify(data, null, 2); refresh();
}
async function noteEvent(id){
  const note = prompt('Review note for this event:', '');
  if (note === null) return;
  const res = await fetch('/api/events/review', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({id, review_note: note})});
  const data = await res.json(); document.getElementById('eventSummary').textContent = JSON.stringify(data, null, 2); refresh();
}
async function deleteSelected(deleteMedia){
  const ids = Array.from(selectedEvents);
  if (!ids.length) { alert('Select at least one event first.'); return; }
  if (!confirm(`Delete ${ids.length} selected event(s)${deleteMedia ? ' and their media files' : ''}?`)) return;
  const res = await fetch('/api/events/delete', {method:'POST', headers:{'content-type':'application/json'}, body:JSON.stringify({ids, delete_media: deleteMedia})});
  const data = await res.json(); selectedEvents.clear(); document.getElementById('eventSummary').textContent = JSON.stringify(data, null, 2); refresh();
}
function exportVisibleEvents(){
  const blob = new Blob([JSON.stringify(currentEvents, null, 2)], {type:'application/json'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob); a.download = `roomsentry-events-${new Date().toISOString().slice(0,10)}.json`; a.click(); URL.revokeObjectURL(a.href);
}
async function loadDailySummary(){
  const date = document.getElementById('eventDate')?.value || new Date().toISOString().slice(0,10);
  const res = await fetch('/api/events/summary?date=' + encodeURIComponent(date));
  const data = await res.json(); document.getElementById('eventSummary').textContent = JSON.stringify(data, null, 2);
}
async function refresh() {
  try {
    const [stateRes, eventsRes] = await Promise.all([fetch('/api/state'), fetch('/api/events?' + eventQuery())]);
    const state = await stateRes.json();
    const events = await eventsRes.json();
    currentEvents = events;
    selectedEvents = new Set(Array.from(selectedEvents).filter(id => events.some(e => Number(e.id) === Number(id))));
    const stale = state.stale;
    setBig('running', state.running && !stale ? 'Running' : (stale ? 'Stale' : 'Stopped'), state.running && !stale ? 'good' : 'bad');
    setBig('armed', state.armed ? 'Armed' : 'Disarmed', state.armed ? 'good' : 'warn');
    setBig('room', state.room_state || 'Unknown', state.room_state === 'PERSON_PRESENT' ? 'bad' : 'good');
    setBig('fps', state.detector_fps ?? '—', '');
    document.getElementById('message').textContent = `${state.message || ''} ${state.heartbeat_age_seconds !== null ? `(heartbeat ${state.heartbeat_age_seconds}s ago)` : ''}`;
    document.getElementById('ack').textContent = state.ack && state.ack.command ? JSON.stringify(state.ack, null, 2) : document.getElementById('ack').textContent;
    const preview = document.getElementById('preview');
    if (state.preview_path) { preview.src = media(state.preview_path) + '?t=' + Date.now(); }
    renderEvents(events);
    const snaps = events.filter(e => e.snapshot_path).slice(0, 36);
    document.getElementById('gallery').innerHTML = snaps.length ? snaps.map(e => `<figure><a href="${media(e.snapshot_path)}" target="_blank"><img src="${media(e.snapshot_path)}" loading="lazy"></a><figcaption>${esc(e.created_at)}<br>${esc(e.event_type)} ${e.important?'⭐':''}</figcaption></figure>`).join('') : '<p>No snapshots match the current filter.</p>';
  } catch (err) { document.getElementById('message').textContent = 'Dashboard refresh failed: ' + err; }
}

(function initZoneEditor(){
  const {img, canvas} = canvasEls();
  img.addEventListener('load', resizeCanvasToImage);
  window.addEventListener('resize', resizeCanvasToImage);
  canvas.addEventListener('pointerdown', ev => { drawing=true; dragStart=pointerNorm(ev); draftZone={...dragStart,x1:dragStart.x,y1:dragStart.y,x2:dragStart.x,y2:dragStart.y,kind:document.getElementById('zoneKind').value,mode:document.getElementById('zoneMode').value,name:document.getElementById('zoneName').value || 'draft'}; canvas.setPointerCapture(ev.pointerId); drawCanvas(); });
  canvas.addEventListener('pointermove', ev => { if(!drawing || !draftZone) return; const p=pointerNorm(ev); draftZone.x2=p.x; draftZone.y2=p.y; drawCanvas(); });
  canvas.addEventListener('pointerup', ev => { if(!drawing || !draftZone) return; const z=draftZone; drawing=false; dragStart=null; draftZone=null; addDraftToZones(z); try{canvas.releasePointerCapture(ev.pointerId);}catch(e){} });
})();
['eventSearch','eventType','eventDate','filterImportant','filterFalsePositive','filterSnapshots','filterClips'].forEach(id => { const el=document.getElementById(id); if(el) el.addEventListener('change', refresh); });
loadZones(); refresh(); setInterval(refresh, 3000);
</script>
</body>
</html>
"""


class ReusableThreadingHTTPServer(ThreadingHTTPServer):
    allow_reuse_address = True


class Handler(BaseHTTPRequestHandler):
    server_version = "RoomSentryDashboard/1.8"

    def _headers(self, status: int = 200, content_type: str = "application/json") -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Cache-Control", "no-store")
        self.end_headers()

    def _json(self, payload: Any, status: int = 200) -> None:
        self._headers(status, "application/json; charset=utf-8")
        self.wfile.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))

    def _body(self) -> bytes:
        length = int(self.headers.get("Content-Length", "0") or "0")
        return self.rfile.read(length) if length else b""

    def do_GET(self) -> None:  # noqa: N802
        config = load_config()
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        if path == "/":
            self._headers(200, "text/html; charset=utf-8")
            self.wfile.write(INDEX_HTML.encode("utf-8"))
            return
        if path == "/api/state":
            self._json(current_state(config))
            return
        if path == "/api/diagnostics":
            self._json(diagnostics(config))
            return
        if path == "/api/zones":
            self._json(zones_payload(config))
            return
        if path == "/api/events":
            qs = urllib.parse.parse_qs(parsed.query)
            limit = int(qs.get("limit", ["100"])[0])
            filters = {k: qs.get(k, [""])[0] for k in ("q", "type", "date", "important", "false_positive", "has_snapshot", "has_clip")}
            self._json(fetch_events(config, limit, filters))
            return
        if path == "/api/events/summary":
            qs = urllib.parse.parse_qs(parsed.query)
            self._json(daily_summary(config, qs.get("date", [""])[0]))
            return
        if path.startswith("/media/"):
            try:
                media_path = safe_media_path(path[len("/media/"):])
                ctype = mimetypes.guess_type(str(media_path))[0] or "application/octet-stream"
                self._headers(200, ctype)
                with media_path.open("rb") as f:
                    self.wfile.write(f.read())
            except FileNotFoundError:
                self._json({"ok": False, "message": "File not found"}, 404)
            except Exception as exc:
                self._json({"ok": False, "message": str(exc)}, 400)
            return
        self._json({"ok": False, "message": "Not found"}, 404)

    def do_POST(self) -> None:  # noqa: N802
        config = load_config()
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/command":
            try:
                data = json.loads(self._body().decode("utf-8") or "{}")
            except Exception:
                self._json({"ok": False, "message": "Bad JSON"}, 400)
                return
            token = str(config.get("dashboard_command_token", "")).strip()
            if token and data.get("token") != token:
                self._json({"ok": False, "message": "Bad dashboard command token"}, 403)
                return
            self._json(write_command(config, str(data.get("command", ""))))
            return
        if parsed.path == "/api/zones":
            try:
                data = json.loads(self._body().decode("utf-8") or "{}")
            except Exception:
                self._json({"ok": False, "message": "Bad JSON"}, 400)
                return
            token = str(config.get("dashboard_command_token", "")).strip()
            if token and data.get("token") != token:
                self._json({"ok": False, "message": "Bad dashboard command token"}, 403)
                return
            result = save_zones(config, data)
            self._json(result, 200 if result.get("ok") else 400)
            return
        if parsed.path == "/api/events/review":
            try:
                data = json.loads(self._body().decode("utf-8") or "{}")
            except Exception:
                self._json({"ok": False, "message": "Bad JSON"}, 400)
                return
            result = update_event_review(config, data)
            self._json(result, 200 if result.get("ok") else 400)
            return
        if parsed.path == "/api/events/delete":
            try:
                data = json.loads(self._body().decode("utf-8") or "{}")
            except Exception:
                self._json({"ok": False, "message": "Bad JSON"}, 400)
                return
            result = delete_events(config, data)
            self._json(result, 200 if result.get("ok") else 400)
            return
        self._json({"ok": False, "message": "Not found"}, 404)

    def log_message(self, fmt: str, *args: Any) -> None:
        print(f"[{time.strftime('%H:%M:%S')}] {fmt % args}")


def main() -> None:
    parser = argparse.ArgumentParser(description="RoomSentry local control dashboard")
    parser.add_argument("--open", action="store_true", help="Open the dashboard in your browser after starting")
    args = parser.parse_args()
    config = load_config()
    host = str(config.get("dashboard_host", "127.0.0.1"))
    port = int(config.get("dashboard_port", 8765))
    url = f"http://{host}:{port}/"
    httpd = ReusableThreadingHTTPServer((host, port), Handler)
    print(f"RoomSentry dashboard running at {url}")
    if host not in {"127.0.0.1", "localhost"}:
        print("WARNING: Dashboard host is not localhost. Do not expose camera/control dashboard publicly.")
    if args.open:
        webbrowser.open(url)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("Stopping dashboard.")


if __name__ == "__main__":
    main()
